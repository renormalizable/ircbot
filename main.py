import asyncio
import re
import time

import config
import client
import simple
import tool
import lang
import api
import acg
import handy

import logging
#logging.basicConfig(level=logging.DEBUG)

loop = asyncio.get_event_loop()

bot = client.Client(loop, config.host, config.port, **config.option)

bot.nick = config.nick
bot.password = config.password
bot.channel = config.channel

@bot.on('CLIENT_CONNECT')
def connect():
    bot.send('NICK', nick=bot.nick)
    bot.send('PASS', password=bot.password)
    bot.send('USER', user=bot.nick, realname='Bot using bottom.py')
    #bot.send('JOIN', channel=bot.channel)


@bot.on('PING')
def keepalive(message):
    bot.send('PONG', message=message)


class dePrefix:
    def __init__(self):
        #self.r = re.compile(r'(?:(\[)?(?P<nick>.+?)(?(1)\]|:) )?(?P<message>.*)')
        self.r = re.compile(r'(\[(?P<nick>.+?)\] )?((?P<to>[^\s\']+?): )?(?P<message>.*)')
    def __call__(self, n, m):
        r = self.r.fullmatch(m).groupdict()
        #return (r['nick'].strip() if r['nick'] else n, r['message'])
        return (r['to'].strip() if r['to'] else r['nick'].strip() if r['nick'] else n, r['message'])
deprefix = dePrefix()

@bot.on('PRIVMSG')
def multiline(nick, target, message):
    (nick, message) = deprefix(nick, message)
    if nick != bot.nick and message[:4] == "'.. ":
        print('multiline')
        l = message[4:].rstrip() + '\n'
        bot.addlines(nick, l)

@bot.on('PRIVMSG')
def importline(nick, target, message):
    (nick, message) = deprefix(nick, message)
    if nick != bot.nick and message[:4] == "':: ":
        print('importline')
        try:
            l = yield from lang.getcode(message[4:].rstrip())
            bot.addlines(nick, l)
            #send("PRIVMSG", target=target, message=l, to=nick, stripspace=False, convert=False)
            #send("PRIVMSG", target=target, message="imported", to=nick, stripspace=False, convert=False)
        except:
            bot.sendm(target, "出错了啦...", to=nick)
            raise

@bot.on('PRIVMSG')
def message(nick, target, message):
    ''' Echo all messages '''

    # Don't echo ourselves
    if nick == bot.nick:
        return
    (nick, message) = deprefix(nick, message)
    # prefix
    if message[0] != "'" or message[:4] == "'.. " or message[:4] == "':: ":
        return

    message = message[1:].rstrip()
    lines = bot.getlines(nick)
    # Direct message to bot
    if target == bot.nick:
        sender = lambda m, **kw: bot.sender(nick, m, **kw)
    # Message in channel
    else:
        sender = lambda m, **kw: bot.sender(target, m, to=nick, **kw)
    return (yield from reply(nick, message, lines, sender))

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
reg = lambda r: re.compile(r, re.IGNORECASE)
func = [(wrap(helper), reg(r"help(\s+(?P<command>\S+))?"))]
func.extend(map(lambda f: (wrap(f[0]), reg(f[1])), simple.func))
func.extend(map(lambda f: (wrap(f[0]), reg(f[1])), tool.func))
func.extend(map(lambda f: (wrap(f[0]), reg(f[1])), api.func))
func.extend(map(lambda f: (wrap(f[0]), reg(f[1])), acg.func))
func.extend(map(lambda f: (wrap(f[0]), reg(f[1])), handy.func))
func.extend(map(lambda f: (f[0], reg(f[1])), lang.func))

@asyncio.coroutine
def reply(nick, message, lines, send):
    try:
        for (f, r) in func:
            arg = r.fullmatch(message)
            if arg:
                print(arg.groupdict())
                #return (yield from f(arg.groupdict(), lines, send))
                t = time.time()
                yield from f(arg.groupdict(), lines, send)
                print(time.time() - t)
        #send('need some help?')
    except:
        send('╮(￣▽￣)╭')
        raise


@asyncio.coroutine
def dump(loop):
    while True:
        print('dump lines')
        print(bot.lines)
        yield from asyncio.sleep(1)

#tasks = [bot.run(), dump(loop)]
tasks = [bot.run()]

loop.run_until_complete(asyncio.wait(tasks))
