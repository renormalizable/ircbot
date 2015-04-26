import asyncio
import re
import time

from . import simple
from . import tool
from . import lang
from . import api
from . import acg
from . import handy

def command(f, r):
    reg = re.compile(r, re.IGNORECASE)

    @asyncio.coroutine
    def wrap(message, lines, send):
        arg = reg.fullmatch(message)
        if arg:
            print(arg.groupdict())
            try:
                t = time.time()
                yield from f(arg.groupdict(), lines, send)
                print(time.time() - t)
            except:
                send('╮(￣▽￣)╭')
                raise
    return wrap

help = {}
help.update(simple.help)
help.update(tool.help)
help.update(api.help)
help.update(acg.help)
help.update(lang.help)

@asyncio.coroutine
def helper(arg, send):
    if arg['command']:
        send('<...> is mandatory, [...] is optional')
        send('{0}: {1}'.format(arg['command'], help[arg['command']]))
    else:
        send('help: help [command] -- "varia 可是 14 岁的\\x0304萌妹子\\x0f哦" by anonymous')
        send('(づ￣ω￣)づ  -->>  ' + ', '.join(sorted(help.keys())))

wrap = lambda f: lambda arg, lines, send: f(arg, send)
func = [command(wrap(helper), r"help(\s+(?P<command>\S+))?")]
func.extend(map(lambda f: command(wrap(f[0]), f[1]), simple.func))
func.extend(map(lambda f: command(wrap(f[0]), f[1]), tool.func))
func.extend(map(lambda f: command(wrap(f[0]), f[1]), api.func))
func.extend(map(lambda f: command(wrap(f[0]), f[1]), acg.func))
func.extend(map(lambda f: command(wrap(f[0]), f[1]), handy.func))
func.extend(map(lambda f: command(      f[0], f[1]), lang.func))

@asyncio.coroutine
def reply(nick, message, lines, send):
    # prefix
    if message[0] != "'" or message[:4] == "'.. " or message[:4] == "':: ":
        return
    msg = message[1:].rstrip()
    coros = [f(msg, lines, send) for f in func]
    #yield from asyncio.gather(*coros)
    yield from asyncio.wait(coros)
