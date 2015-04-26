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
files = ['simple', 'tool', 'lang', 'api', 'acg', 'handy']

modules = [importlib.import_module(path + f) for f in files]

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
    func = f if len(inspect.signature(f).parameters) == 3 else (lambda arg, lines, send: f(arg, send))
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

@asyncio.coroutine
def reply(nick, message, bot, send):
    # prefix
    if message[0] != "'" or message[:4] == "'.. " or message[:4] == "':: ":
        return
    msg = message[1:].rstrip()
    lines = bot.getlines(nick)
    print(nick, msg, lines)
    coros = [f(msg, lines, send) for f in func]
    #yield from asyncio.gather(*coros)
    yield from asyncio.wait(coros)
