import asyncio
import re

import config
import client
import command

import logging
#logging.basicConfig(level=logging.DEBUG)

loop = asyncio.get_event_loop()

bot = client.Client(loop, config.host, config.port, **config.option)

bot.nick = config.nick
bot.login = config.login
bot.password = config.password
bot.channel = config.channel


@bot.on('CLIENT_CONNECT')
def connect():
    bot.send('NICK', nick=bot.login)
    bot.send('PASS', password=bot.password)
    bot.send('USER', user=bot.login, realname='Bot using bottom.py')
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
    lines = bot.getlines(nick)
    print(nick, target, message, lines)

    # Direct message to bot
    if target == bot.nick:
        sender = lambda m, **kw: bot.sender(nick, m, **kw)
    # Message in channel
    else:
        sender = lambda m, **kw: bot.sender(target, m, to=nick, **kw)

    return (yield from command.reply(nick, message, lines, sender))


@asyncio.coroutine
def dump(loop):
    while True:
        print('dump lines')
        print(bot.lines)
        yield from asyncio.sleep(1)

#tasks = [bot.run(), dump(loop)]
tasks = [bot.run()]

loop.run_until_complete(asyncio.wait(tasks))
