import asyncio
import re
import time
import os
import importlib
import inspect

#dir = './modules/commands'
# no dir allowed
#file = [f[:-3] for f in os.listdir(dir) if f.endswith('.py') and f != '__init__.py']

path = 'modules.commands.'
#path = '.'
files = ['simple', 'tool', 'lang', 'api', 'acg', 'handy']
modules = [importlib.reload(importlib.import_module(path + f)) for f in files]
table = dict(zip(files, modules))

help = dict(sum((getattr(m, 'help', []) for m in modules), []))

@asyncio.coroutine
def helper(arg, send):
    if arg['command']:
        send('<...> is mandatory, [...] is optional')
        send('{0}: {1}'.format(arg['command'], help[arg['command']]))
    else:
        send('help: help [command] -- "varia 可是 14 岁的\\x0304萌妹子\\x0f哦" by anonymous')
        send('(づ￣ω￣)づ  -->>  ' + ', '.join(sorted(help.keys())))

def command(f, r):
    func = f if inspect.signature(f).parameters.get('lines') else (lambda arg, lines, send: f(arg, send))
    reg = re.compile(r, re.IGNORECASE)

    @asyncio.coroutine
    def wrap(message, lines, send):
        arg = reg.fullmatch(message)
        if arg:
            print(arg.groupdict())
            try:
                t = time.time()
                yield from func(arg.groupdict(), lines, send)
                print(time.time() - t)
            except:
                send('╮(￣▽￣)╭')
                raise
    return wrap

func = [command(f[0], f[1]) for f in sum((getattr(m, 'func', []) for m in modules), [(helper, r"help(\s+(?P<command>\S+))?")])]

class Get:
    def __init__(self):
        self.l = ''
    def __call__(self, l, n=-1, **kw):
        if n < 0:
            self.l += l + '\n'
        else:
            for (i, m) in enumerate(l):
                if i >= n:
                    break
                self.l += m + '\n'

@asyncio.coroutine
def reply(nick, message, bot, send):
    # prefix
    #if message[0] != "'" or message[:4] == "'.. " or message[:4] == "':: ":
    #    return
    if message[0] == "'":
        if message[:4] in ["'.. ", "':: "]:
            return
        output = True
    elif message[0] == '"':
        output = False
    else:
        return

    msg = message[1:].rstrip()
    lines = bot.getlines(nick)[:-1]
    print(nick, msg, lines)

    if output:
        coros = [f(msg, lines, send) for f in func]
        yield from asyncio.wait(coros)
    else:
        get = Get()
        coros = [f(msg, lines, get) for f in func]
        yield from asyncio.wait(coros)
        bot.addlines(nick, get.l[:-1])

    #yield from asyncio.gather(*coros)
    #yield from asyncio.wait(coros)

@asyncio.coroutine
def getcode(url):
    return (yield from table['lang'].getcode(url))
