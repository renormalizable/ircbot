import bottom
import asyncio
import re

import config
import simple
import tool
import eval
import api
import acg

import logging
#logging.basicConfig(level=logging.DEBUG)

bot = bottom.Client(config.host, config.port, **config.option)

bot.nick = config.nick
bot.password = config.password
bot.channel = config.channel

bot.lines = ''

@bot.on('CLIENT_CONNECT')
def connect():
    bot.send('NICK', nick=bot.nick)
    bot.send('PASS', password=bot.password)
    bot.send('USER', user=bot.nick, realname='Bot using bottom.py')
    #bot.send('JOIN', channel=bot.channel)


@bot.on('PING')
def keepalive(message):
    bot.send('PONG', message=message)

def normalize(message):
    dict = {
        '　': '  ',
        '，': ', ',
        '。': '. ',
        '！': '! ',
        '？': '? ',
        '：': ': ',
    }
    line = map(lambda l: ' '.join(l.split()), str(message).splitlines())
    line = filter(lambda l: l, line)
    line = map(lambda l: l.translate(str.maketrans(dict)), line)
    return '\x0304\\n\x0f '.join(line)

def send(command, *, target='', message='', to='', color=None):
    # (512 - 2) / 3 = 170
    # 430 bytes should be safe
    limit = 430

    #normalize = lambda f: '\x0304\\n\x0f '.join(map(lambda l: ' '.join(l.split()), str(f).splitlines()))
    message = ((to + ': ') if to else '') + normalize(message)
    print(message)
    m = list(map(lambda c: len(c.encode('utf-8')), message))
    while len(m) > 0:
        i = 0
        s = 0
        while i < len(m):
            s = s + m[i]
            if s > limit:
                break
            i = i + 1
        print(sum(m[:i]))
        bot.send(command, target=target, message=message[:i])
        message = message[i:]
        m = m[i:]


@bot.on('PRIVMSG')
def message(nick, target, message):
    ''' Echo all messages '''

    # Don't echo ourselves
    if nick == bot.nick:
        return
    # prefix
    #print('lines')
    #print(bot.lines)
    if message[0] != "'":
        return
    if message[:4] == "'.. ":
        bot.lines = bot.lines + message[4:].rstrip() + '\n'
        return
    message = message[1:].rstrip()
    # Direct message to bot
    if target == bot.nick:
        yield from reply(nick, message, bot.lines, lambda m: send("PRIVMSG", target=nick, message=m))
    # Message in channel
    else:
        yield from reply(nick, message, bot.lines, lambda m: send("PRIVMSG", target=target, message=m, to=nick))
        #yield from reply(nick, message, lambda m: send("PRIVMSG", target=target, message=m))

    bot.lines = ''

help = {}
help.update(simple.help)
help.update(tool.help)
help.update(api.help)
help.update(acg.help)
help.update(eval.help)

@asyncio.coroutine
def helper(arg, send):
    if arg['command']:
        send('<...> is mandatory, [...] is optional')
        send('{0}: {1}'.format(arg['command'], help[arg['command']]))
    else:
        send('(づ￣ω￣)づ  -->>  ' + ', '.join(sorted(help.keys())))

wrap = lambda f: lambda arg, lines, send: f(arg, send)
reg = lambda r: re.compile(r, re.IGNORECASE)
func = [(wrap(helper), reg(r"help(\s+(?P<command>\S+))?"))]
func.extend(map(lambda f: (wrap(f[0]), reg(f[1])), simple.func))
func.extend(map(lambda f: (wrap(f[0]), reg(f[1])), tool.func))
func.extend(map(lambda f: (wrap(f[0]), reg(f[1])), api.func))
func.extend(map(lambda f: (wrap(f[0]), reg(f[1])), acg.func))
func.extend(map(lambda f: (f[0], reg(f[1])), eval.func))

@asyncio.coroutine
def reply(nick, message, lines, send):
    try:
        for (f, r) in func:
            arg = r.fullmatch(message)
            if arg:
                print(arg.groupdict())
                return (yield from f(arg.groupdict(), lines, send))
    except:
        send('╮(￣▽￣)╭')
        raise


asyncio.get_event_loop().run_until_complete(bot.run())
