import asyncio
import re
import time
import os
import importlib
import inspect
import traceback

from ..timeoutdict import TimeoutDict

path = 'modules.commands.'
files = ['common', 'simple', 'util', 'tool', 'lang', 'api', 'acg', 'handy', 'multiline']
modules = [importlib.reload(importlib.import_module(path + f)) for f in files]
table = dict(zip(files, modules))

Get = table['common'].Get
fetcher = table['multiline'].fetcher

help = dict(sum((getattr(m, 'help', []) for m in modules), []))


@asyncio.coroutine
def helper(arg, send):
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

    @asyncio.coroutine
    def wrap(message, lines, send, meta):
        arg = reg.fullmatch(message)
        if arg:
            print(arg.groupdict())
            try:
                t = time.time()
                d = arg.groupdict()
                d.update(meta)
                yield from func(d, lines, send)
                print(time.time() - t)
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


class Queue(TimeoutDict):

    @asyncio.coroutine
    def put(self, key, value, func):
        try:
            queue = self.__getitem__(key)
            yield from queue[0].put(value)
            self.__setitem__(key, queue)
        except KeyError:
            queue = [asyncio.Queue(), asyncio.async(func(key))]
            yield from queue[0].put(value)
            self.__setitem__(key, queue)

    @asyncio.coroutine
    def get(self, key, default=None):
        try:
            return (yield from self.__getitem__(key)[0].get())
        except KeyError:
            return default

    def __delitem__(self, key):
        print('__delitem__')
        item = self.d.pop(key)
        item[0][1].cancel()
        item[1].cancel()
        #print(item)

    # not safe to cleanup
    # if some command runs longer than timeout
    def __cleanup__(self, key):
        print('__clean__', key, self.d)
        self.pop(key, None)
        print('__clean__', key, self.d)

queue = Queue()


@asyncio.coroutine
def execute(msg, lines, send, meta):
    coros = [f(msg, lines, send, meta) for f in func]

    status = yield from asyncio.gather(*coros)
    return any(status)


@asyncio.coroutine
def reply(bot, nick, message, send):
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
    #send(repr(lines))
    #print(nick, msg, lines)
    print(nick, msg)
    meta = {'meta': {
        'bot': bot,
        'nick': nick,
        'send': send,
        'command': lambda msg, lines, send: execute(msg, lines, send, meta),
    }}

    #yield from asyncio.sleep(1)
    success = yield from execute(msg, lines, sender, meta)
    print('success?', success)

    if not success and lines:
        line.append(nick, lines)


@asyncio.coroutine
def multiline(bot, nick, message, send):
    if message[:4] == "'.. " or message == "'..":
        print('multiline')
        l = [message[4:].rstrip()]
        line.append(nick, l)


@asyncio.coroutine
def fetchline(bot, nick, message, send):
    if message[:4] == "':: ":
        print('fetchline')
        try:
            l = yield from fetcher(message[4:].rstrip())
            line.append(nick, l)
        except:
            send('出错了啦...')
            traceback.print_exc()


@asyncio.coroutine
def process(nick):
    while True:
        item = yield from queue.get(nick)

        if item == None:
            print('process break')
            break

        #print(nick, item)

        coros = [f(item[0], nick, item[1], item[2]) for f in [reply, multiline, fetchline]]
        # gather() cancels coros when process() is cancelled
        yield from asyncio.gather(*coros)

        #print('process')
        #yield from asyncio.sleep(1)


@asyncio.coroutine
def dispatch(bot, nick, message, send):
    if message[:1] not in ["'", '"']:
        return

    yield from queue.put(nick, (bot, message, send), process)

privmsg = [
    #reply,
    #multiline,
    #fetchline,
    dispatch,
]
