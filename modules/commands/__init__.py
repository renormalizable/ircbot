import asyncio
import re
import time
import os
import importlib
import inspect

common = importlib.reload(importlib.import_module('modules.commands.common'))
Get = common.Get

#dir = './modules/commands'
# no dir allowed
#file = [f[:-3] for f in os.listdir(dir) if f.endswith('.py') and f != '__init__.py']

path = 'modules.commands.'
#path = '.'
files = ['simple', 'util', 'tool', 'lang', 'api', 'acg', 'handy']
modules = [importlib.reload(importlib.import_module(path + f)) for f in files]
table = dict(zip(files, modules))

help = dict(sum((getattr(m, 'help', []) for m in modules), []))

@asyncio.coroutine
def helper(arg, send):
    c = arg['command']
    if c:
        h = help[c]
        send('<...> is mandatory, [...] is optional, (...) also accepts multiline input')
        send('\\x0300{0}:\\x0f {1}'.format(c, h))
    else:
        send('\\x0300help:\\x0f help [command] -- "varia 可是 14 岁的\\x0304萌妹子\\x0f哦" by anonymous')
        send('(づ￣ω￣)づ  -->>  ' + ' '.join(sorted(help.keys())))
        send('try \\x0300help \\x1fcommand\\x1f\\x0f to find out more~')

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
def reply(nick, message, bot, send):
    # prefix
    if message[0] == "'":
        if message[:4] in ["'.. ", "':: "]:
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
def getcode(url):
    return (yield from table['lang'].getcode(url))
