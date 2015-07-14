import asyncio
import re
import time
import os
import importlib
import inspect

path = 'modules.commands.'
files = ['simple', 'util', 'tool', 'lang', 'api', 'acg', 'handy']
modules = [importlib.reload(importlib.import_module(path + f)) for f in files]
table = dict(zip(files, modules))

common = importlib.reload(importlib.import_module(path + 'common'))
Get = common.Get
multiline = importlib.reload(importlib.import_module(path + 'multiline'))
fetcher = multiline.fetcher

help = dict(sum((getattr(m, 'help', []) for m in modules), []))

@asyncio.coroutine
def helper(arg, send):
    c = arg['command']
    if c:
        h = help[c]
        send('<...> is mandatory, [...] is optional, (...) also accepts multiline input')
        send('\\x0300{0}:\\x0f {1}'.format(c, h))
    else:
        send('\\x0300help:\\x0f help [command] -- "{0} 可是 14 岁的\\x0304萌妹子\\x0f哦" by anonymous'.format(arg['meta']['bot'].nick))
        send('(づ￣ω￣)づ  -->>  ' + ' '.join(sorted(help.keys())))
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
                #raise
                return False
            return True
        return False
    return wrap

func = [command(f[0], f[1]) for f in sum((getattr(m, 'func', []) for m in modules), [(helper, r"help(\s+(?P<command>\S+))?")])]

@asyncio.coroutine
def execute(msg, lines, send, meta):
    coros = [f(msg, lines, send, meta) for f in func]

    #yield from asyncio.wait(coros)
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
        sender = Get(lambda line: bot.addlines(nick, line))
    else:
        return

    msg = message[1:].rstrip()
    lines = bot.getlines(nick)
    #send(repr(lines))
    #print(nick, msg, lines)
    print(nick, msg)
    meta = {'meta': {
        'bot': bot,
        'nick': nick,
        'send': send,
        'command': lambda msg, lines, send: execute(msg, lines, send, meta),
    }}

    success = yield from execute(msg, lines, sender, meta)
    print('success?', success)

    if not success and lines:
        bot.addlines(nick, lines)

@asyncio.coroutine
def multiline(bot, nick, message, send):
    if message[:4] == "'.. " or message == "'..":
        print('multiline')
        l = [message[4:].rstrip()]
        bot.addlines(nick, l)

@asyncio.coroutine
def fetchline(bot, nick, message, send):
    if message[:4] == "':: ":
        print('fetchline')
        try:
            l = yield from fetcher(message[4:].rstrip())
            bot.addlines(nick, l)
        except:
            send('出错了啦...')
            raise

privmsg = [
    reply,
    multiline,
    fetchline,
]
