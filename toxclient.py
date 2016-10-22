import asyncio
import importlib

import pytriam

from common import dePrefix, Normalize, splitmessage


class ToxClient(pytriam.Messager):

    def __init__(self, loop, tox, config):
        super().__init__(tox)

        self.loop = loop

        self.nick = self.bot.get('name')
        self.config = importlib.import_module(config)
        self.key = self.config.key

        self.msglimit = 1300

        self.deprefix = dePrefix()
        self.normalize = Normalize(newline='\n', escape=False, convert=False)
        self.modules = importlib.import_module('modules')

    def group_get_nick(self, target, peer):
        return self.core.group_peername(target, peer)

    def get_nick(self, target):
        return self.core.friend_get_name(target)

    def on(self, name):
        def on_event(fn):
            if name not in self.events:
                self.events[name] = list()
            self.events[name].append(asyncio.coroutine(fn))
        return on_event

    def trigger(self, name, arguments):
        print('trigger', name, arguments)
        @asyncio.coroutine
        def task():
            func = self.events.get(name)
            if func:
                coros = [f(self, arguments) for f in func]
                yield from asyncio.wait(coros)

        self.loop.call_soon(asyncio.async, task())

    @asyncio.coroutine
    def run(self):
        self.trigger('tox.init', {})
        checked = False

        while True:
            status = self.core.self_get_connection_status()

            if not checked and status:
                self.trigger('tox.connect', {
                    'status': "Connected"
                })
                checked = True

            if checked and not status:
                self.trigger('tox.connect', {
                    'status': "Disconnected"
                })
                checked = False

            try:
                self.core.iterate()
            except UnicodeDecodeError:
                print('ignore unicode error')
            yield from asyncio.sleep(0.01)

    def send(self, command, *, target=0, message=''):
        if command == 'friend':
            #super().send(target, message)
            self.core.friend_send_message(target, message)
        elif command == 'group':
            self.core.group_message_send(target, message)
        else:
            pass

    def reload(self):
        self.modules = importlib.reload(self.modules)
        self.config = importlib.reload(self.config)
        self.key = self.config.key

    def sendm(self, target, message, *, command='PRIVMSG', to='', raw=False, mlimit=0, color=None, **kw):
        prefix = '' if raw else (to + ': ') if to else ''
        message = self.normalize(message, **kw)
        print(repr(message))
        for (i, m) in enumerate(splitmessage(message, self.msglimit)):
            if mlimit > 0 and i >= mlimit:
                self.send(command, target=target, message=prefix + '太多了啦...')
                break
            self.send(command, target=target, message=prefix + m)

    def sendl(self, target, line, n, *, llimit=0, **kw):
        sent = False
        for (i, m) in enumerate(line):
            if llimit > 0 and i >= llimit:
                command = kw.get('command', '')
                to = kw.get('to', '')
                prefix = (to + ': ') if to else ''
                self.send(command, target=target, message=prefix + '太长了啦...')
                break
            self.sendm(target, m, **kw)
            sent = True
            if n > 0 and i >= (n - 1):
                break
        if not sent:
            raise Exception()

    def sender(self, target, content, *, n=-1, llimit=-1, **kw):
        if n < 0:
            self.sendm(target, content, **kw)
        else:
            if llimit < 0:
                self.sendl(target, content, n, **kw)
            else:
                self.sendl(target, content, n, llimit=llimit, **kw)
