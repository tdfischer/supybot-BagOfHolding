###
# -*- coding: utf-8 -*-
# Copyright (c) 2009-2014, Torrie Fischer
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import supybot.utils as utils
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import random
import re


class BagOfHolding(callbacks.Plugin):
    """Add the help for "@plugin help BagOfHolding" here
    This should describe *how* to use this plugin."""
    def random(self, irc, msg, args, channel):
        """[<channel>]

        Pulls a random object out of the bag and puts it back.
        """
        contents = self.registryValue('contents', channel)
        irc.reply(random.choice(contents))
    random = wrap(random, ['channeldb'])

    def hit(self, irc, msg, args, channel, target):
        """[<channel>] <target>

        Pulls a random object out of the bag and hits them with it, putting it
        back in the end.
        """
        contents = self.registryValue('contents', channel)
        actions = (
            "hits %(who)s around a bit with %(what)s",
            "smacks %(who)s with %(what)s",
            "grabs %(who)s and savagely beats them with %(what)s",
            "hits %(what)s around a bit with %(who)s",
            "bodyslams %(who)s and whails on them with %(what)s"
        )
        irc.reply(random.choice(actions)%{'who':target,'what':random.choice(contents)}, action = True)
    hit = wrap(hit, ['channeldb', 'text'])

    def transmogrify(self, irc, msg, args, channel):
        """[<channel>]

        Pulls a random item from the bag and transforms it into another"""
        contents = self.registryValue('contents', channel)
        if (len(contents) < 1):
            irc.reply("can't transmogrify an empty bag", action = True)
            return
        item = random.choice(contents)
        contents.remove(item)
        if (len(self.registryValue('history', channel)) == 0):
            result = "something almost quite but not entirely unlike tea"
        else:
            result = random.choice(self.registryValue('history', channel))
        contents.append(result)
        self.setRegistryValue('contents', contents, channel)
        irc.reply("derived %s from %s!"%(result, item))
    transmogrify = wrap(transmogrify, ['channeldb'])

    def combine(self, irc, msg, args, channel, number):
        """[<channel>] <number>

        Pulls <number> items out of the bag and combines them into a humorous
        result"""
        contents = self.registryValue('contents', channel)
        number = int(number)
        if (len(contents) < number):
            irc.error("I only have %s things in my bag."%(len(contents)))
            return
        if (number < 2):
            irc.error("I can only combine at least two items, no fewer.")
            return
        items = []
        for i in range(0, number):
            item = random.choice(contents)
            contents.remove(item)
            items.append(item)
        if (len(self.registryValue('history', channel)) == 0):
            result = "something almost quite but not entirely unlike tea"
        else:
            result = random.choice(self.registryValue('history', channel))
        contents.append(result)
        self.setRegistryValue('contents', contents, channel)
        if (len(items) == 2):
            irc.reply("combined %s and %s to create %s!"%(items[0], items[1], result), action = True)
        else:
            irc.reply("combined %s, and %s to create %s!"%(', '.join(items[0:-1]), items[-1], result), action = True)
    combine = wrap(combine, ['channeldb', 'int'])

    def _removeItem(self, channel, thing):
        contents = self.registryValue('contents', channel)
        if (thing in contents):
            contents.remove(thing)
            self.setRegistryValue('contents', contents, channel)
            return thing
        return None

    def _size(self, channel):
        contents = self.registryValue('contents', channel)
        if (len(contents) == 0):
            return 0
        return reduce(lambda x,y: x+y,
                    map(lambda x: len(x),
                        contents))

    def _addItem(self, channel, thing):
        contents = self.registryValue('contents', channel)
        size = self.registryValue('size', channel)
        dropped = []
        while(size > 0 and self._size(channel)+len(thing) > size and len(contents) > 0):
            item = random.choice(contents)
            contents.remove(item)
            dropped.append(item)
        contents.insert(0, thing)
        self.setRegistryValue('contents', contents, channel)
        history = self.registryValue('history', channel)
        if (thing not in history):
            history.append(thing)
        self.setRegistryValue('history', history, channel)
        return dropped

    def weight(self, irc, msg, args, channel):
        """[<channel>]

        Returns the weight of the bag"""
        irc.reply(self._size(channel))
    weight = wrap(weight, ['channeldb'])

    def hold(self, irc, msg, args, channel, thing):
        """[<channel>] <thing>

        Puts <thing> into the bag of holding.
        """
        dropped = self._addItem(channel, thing)
        if (len(dropped) == 0):
            irc.reply("picked up %s."%thing, action = True)
        elif (len(dropped) == 1):
            irc.reply("picked up %s, but dropped %s."%(thing, dropped[0]), action = True)
        else:
            irc.reply("picked up %s, but dropped %s, and %s."%(thing, ', '.join(dropped[0:-1]), dropped[-1]), action = True)
    hold = wrap(hold, ['channeldb', 'text'])

    def conjure(self, irc, msg, args, channel):
        """[<channel>]

        Conjures up a random item from the history and puts it in the bag.
        Fails when the bag is full.
        """
        if (self._size(channel) < self.registryValue('size', channel)):
            history = self.registryValue('history', channel)
            item = random.choice(history)
            methods = (
                "spins up the LHC to create %s",
                "pulls %s out of your ear",
                "wills %s into being",
                "conjures up %s with the +3 staff of conjuring",
                "calls forth %s from the void",
                "invents %s",
                "ponders %s into existance",
                "considers the set of all real numbers and reduces it to %s",
                "casts a void*, resulting in %s",
                "drags %s out from behind a curtain",
                "orders an airstrike consisting of two nukes and %s",
                "orders a 6\" BLT with a side of %s",
                "pulls %s out of his bag of holding",
                "ヽ（ ﾟヮﾟ）ﾉ.・ﾟ*｡・+☆ %s",
                "(╯‵Д′)╯彡 %s",
            )
            method = random.choice(methods)
            irc.reply(method%(item), action=True)
            self._addItem(channel, item)
        else:
            methods = (
                "thinks real hard to no avail",
                "calls out into the void with no result",
                "can't conjure anything when the bag is full",
                "needs more pylons"
            )
            irc.reply(random.choice(methods), action = True)
    conjure = wrap(conjure, ['channeldb'])

    def doPrivmsg(self, irc, msg):
        if (ircmsgs.isAction(msg) and irc.isChannel(msg.args[0])):
            self.log.debug("Trying to match against '%s'", ircmsgs.unAction(msg))
            matches = re.match('^(hands|tosses|throws|gives)\s+(.+?)\s+(.+)', ircmsgs.unAction(msg))
            if (matches):
                (verb, person, thing) = matches.groups()
                self.log.debug("Matches: %s", matches.groups())
                if (person.lower() == irc.nick.lower()):
                    dropped = self._addItem(plugins.getChannel(msg.args[0]),thing)
                    if (len(dropped) == 0):
                        irc.reply("picked up %s."%thing, action = True)
                    elif (len(dropped) == 1):
                        irc.reply("picked up %s, but dropped %s."%(thing, dropped[0]), action = True)
                    else:
                        irc.reply("picked up %s, but dropped %s, and %s."%(thing, ', '.join(dropped[0:-1]), dropped[-1]), action = True)
            


Class = BagOfHolding


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
