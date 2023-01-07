import asyncio
import collections
import importlib

import bottom

from common import dePrefix, Normalize, splitmessage


class Client(bottom.Client):

    def __init__(self, config):
        self.config = importlib.import_module(config)
        super().__init__(self.config.host, self.config.port, **self.config.option)
        # https://github.com/numberoverzero/bottom/issues/60
        self._events = collections.defaultdict(lambda: asyncio.Event())

        self.admin = self.config.admin
        self.nick = self.config.nick
        self.login = self.config.login
        self.password = self.config.password
        self.channel = self.config.channel
        self.key = self.config.key

        # (512 - 2) / 3 = 170
        # 430 bytes should be safe
        # not really, for #archlinux-cn-offtopic
        self.msglimit = 420

        self.deprefix = dePrefix()
        self.normalize = Normalize()
        self.modules = importlib.import_module('modules')

    ## fully async
    #@asyncio.coroutine
    #def trigger(self, event, **kwargs):
    #    partials = self.__partials__[event]
    #    tasks = [func(**kwargs) for func in partials]
    #    if not tasks:
    #        return
    #    asyncio.async(asyncio.wait(tasks))

    def reload(self):
        self.modules = importlib.reload(self.modules)
        self.config = importlib.reload(self.config)
        self.key = self.config.key

    def sendm(self, target, message, *, command='PRIVMSG', to='', raw=False, mlimit=0, color=None, **kw):
        prefix = (to + ': ') if to else ''
        message = ('' if raw else prefix) + self.normalize(message, **kw)
        print('send: {}'.format(repr(message)))
        for (i, m) in enumerate(splitmessage(message, self.msglimit)):
            if mlimit > 0 and i >= mlimit:
                self.send(command, target=target, message=prefix + '太多了啦...')
                break
            self.send(command, target=target, message=m)

    #def sendl(self, target, line, n, *, llimit=0, loffset=0, **kw):
    #    sent = False

    #    if loffset > 0:
    #        pass

    #    for (i, m) in enumerate(line):
    #        if n > 0 and i >= n:
    #            break
    #        if llimit > 0 and i >= llimit:
    #            #d = {k: kw[k] for k in ['command', 'to'] if k in kw}
    #            #self.sendm(target, '太长了啦...', **d)
    #            command = kw.get('command', 'PRIVMSG')
    #            to = kw.get('to', '')
    #            prefix = (to + ': ') if to else ''
    #            self.send(command, target=target, message=prefix + '太长了啦...')
    #            break
    #        self.sendm(target, m, **kw)
    #        sent = True
    #    if not sent:
    #        raise Exception()

    #def sender(self, target, content, *, n=-1, llimit=-1, loffest=-1, **kw):
    #    if n < 0:
    #        self.sendm(target, content, **kw)
    #    else:
    #        d = {}
    #        if llimit >= 0:
    #            d['llimit'] = llimit
    #        if loffset >=0:
    #            d['loffset'] = loffset
    #        self.sendl(target, content, n, **d, **kw)
    #        #if llimit < 0:
    #        #    self.sendl(target, content, n, **kw)
    #        #else:
    #        #    self.sendl(target, content, n, llimit=llimit, **kw)

    def sendl(self, target, line, n, *, llimit=0, **kw):
        sent = False
        for (i, m) in enumerate(line):
            if llimit > 0 and i >= llimit:
                #d = {k: kw[k] for k in ['command', 'to'] if k in kw}
                #self.sendm(target, '太长了啦...', **d)
                command = kw.get('command', 'PRIVMSG')
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
