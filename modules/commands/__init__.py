import asyncio
import importlib
import inspect
import os
import re
import time
import traceback

from ..timeoutdict import TimeoutDict


path = 'modules.commands.'
files = ['common', 'simple', 'util', 'tool', 'lang', 'api', 'ime', 'acg', 'handy', 'multiline', 'blug']
modules = [importlib.reload(importlib.import_module(path + f)) for f in files]
table = dict(zip(files, modules))

Get = table['common'].Get
fetcher = table['multiline'].fetcher
cmdsub = table['util'].cmdsub

help = dict(sum((getattr(m, 'help', []) for m in modules), []))


async def helper(arg, send):
    c = arg['command']
    if c:
        h = help[c]
        send('<...> is mandatory, [...] is optional, (...) also accepts multiline input')
        #send('\\x0300{0}:\\x0f {1}'.format(c, h))
        send('\\x02{0}:\\x0f {1}'.format(c, h))
    else:
        #send('\\x0300help:\\x0f help [command] -- "{0} 可是 14 岁的\\x0304萌妹子\\x0f哦" by anonymous'.format(arg['meta']['bot'].nick))
        send('\\x02help:\\x0f help [command] -- "{0} 可是 14 岁的\\x0304萌妹子\\x0f哦" by anonymous'.format(arg['meta']['bot'].nick))
        #send('(づ￣ω￣)づ  -->>  ' + ' '.join(sorted(help.keys())))
        send('(っ‾ω‾)っ  -->>  ' + ' '.join(sorted(help.keys())))
        #send('try "\\x0300help \\x1fcommand\\x1f\\x0f" to find out more~')


def command(f, r):
    func = f if inspect.signature(f).parameters.get('lines') else (lambda arg, lines, send: f(arg, send))
    reg = re.compile(r, re.IGNORECASE)

    async def wrap(message, lines, send, meta):
        arg = reg.fullmatch(message)
        if arg:
            try:
                name = f.__qualname__
            except AttributeError:
                name = f.__class__.__qualname__
            print('{0}: {1}'.format(name, arg.groupdict()))
            try:
                t = time.time()
                d = arg.groupdict()
                d.update(meta)
                await func(d, lines, send)
                print('time: {} s'.format(time.time() - t))
            except Exception as e:
                err = ' sad story... ' + str(e) if str(e) else ''
                send('╮(￣▽￣)╭' + err)
                traceback.print_exc()
                return False
            return True
        return False

    return wrap

func = [command(f[0], f[1]) for f in sum((getattr(m, 'func', []) for m in modules), [(helper, r"help(\s+(?P<command>\S+))?")])]


class Line(TimeoutDict):

    def append(self, nick, l):
        self.__setitem__(nick, self.get(nick, []) + l)

    def __cleanup__(self, key):
        self.pop(key, None)

line = Line()


# queue will wait self.timeout starting from the last put before calling __cleanup__
class Queue(TimeoutDict):

    async def put(self, key, value, func):
        try:
            queue = self.__getitem__(key)
        except KeyError:
            queue = [asyncio.Queue(), asyncio.ensure_future(func(key))]
        await queue[0].put(value)
        self.__setitem__(key, queue)

    async def get(self, key, default=None):
        try:
            return (await self.__getitem__(key)[0].get())
        except KeyError:
            return default

    def __delitem__(self, key):
        item = self.d.pop(key)
        item[0][1].cancel()
        item[1].cancel()

    # not safe to cleanup
    # if some command runs longer than timeout
    def __cleanup__(self, key):
        self.pop(key, None)
        print('queue clean up: {}'.format(key))

queue = Queue()


async def execute(msg, lines, send, meta):
    msg = await cmdsub(meta['meta']['command'], msg)
    print('execute: {}'.format(repr(msg)))
    coros = [f(msg, lines, send, meta) for f in func]

    status = await asyncio.gather(*coros)
    return any(status)


async def reply(bot, nick, message, send):
    # prefix
    if message[0] == "'":
        if message[:3] in ["'..", "'::"]:
            return
        sender = send
    elif message[0] == '"':
        sender = Get(lambda l: line.append(nick, l))
    else:
        return

    msg = message[1:].rstrip()
    lines = line.pop(nick, [])
    meta = {'meta': {
        'bot': bot,
        'nick': nick,
        'send': send,
        'save': Get(lambda l: line.append(nick, l)),
        'command': lambda msg, lines, send: execute(msg, lines, send, meta),
    }}
    print('reply: {} {}'.format(nick, repr(msg)))

    success = await execute(msg, lines, sender, meta)
    print('success?', success)

    if not success and lines:
        line.append(nick, lines)


async def multiline(bot, nick, message, send):
    if message[:4] == "'.. " or message == "'..":
        msg = message[4:].rstrip()
        print('multiline: {}'.format(repr(msg)))
        l = [msg]
        line.append(nick, l)


async def fetchline(bot, nick, message, send):
    if message[:4] == "':: ":
        msg = message[4:].rstrip()
        print('fetchline: {}'.format(repr(msg)))
        try:
            l = await fetcher(msg)
            line.append(nick, l)
        except:
            send('出错了啦...')
            traceback.print_exc()


async def process(nick):
    while True:
        item = await queue.get(nick)

        if item == None:
            print('process return')
            return

        coros = [f(item[0], nick, item[1], item[2]) for f in [reply, multiline, fetchline]]
        # gather() cancels coros when process() is cancelled
        await asyncio.gather(*coros)


async def dispatch(bot, nick, message, send):
    if message[:1] not in ["'", '"']:
        return
    if message[:2] == "'!":
        return

    await queue.put(nick, (bot, message, send), process)


privmsg = [
    #reply,
    #multiline,
    #fetchline,
    dispatch,
]
