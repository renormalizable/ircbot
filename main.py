import asyncio

import config
import client

import logging
#logging.basicConfig(level=logging.DEBUG)

loop = asyncio.get_event_loop()

bot = client.Client(loop, config.host, config.port, **config.option)

bot.admin = config.admin
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


#@bot.on('PRIVMSG')
#def message(nick, target, message):
#    ''' Echo all messages '''
#
#    # Don't echo ourselves
#    if nick == bot.nick:
#        return
#
#    (nick, message) = bot.deprefix(nick, message)
#
#    # Direct message to bot
#    if target == bot.nick:
#        sender = lambda m, **kw: bot.sender(nick, m, **kw)
#    # Message in channel
#    else:
#        sender = lambda m, **kw: bot.sender(target, m, to=nick, **kw)
#
#    return (yield from bot.modules.reply(nick, message, bot, sender))


@bot.on('PRIVMSG')
def privmsg(nick, target, message):
    if nick == bot.nick:
        return

    (nick, message) = bot.deprefix(nick, message)
    if target == bot.nick:
        sender = lambda m, **kw: bot.sender(nick, m, **kw)
    else:
        sender = lambda m, **kw: bot.sender(target, m, to=nick, **kw)

    coros = [f(bot, nick, message, sender) for f in bot.modules.privmsg]

    return (yield from asyncio.wait(coros))


@asyncio.coroutine
def dump(loop):
    while True:
        print('dump lines')
        print(bot.lines)
        yield from asyncio.sleep(1)

#tasks = [bot.run(), dump(loop)]
tasks = [bot.run()]

loop.run_until_complete(asyncio.wait(tasks))
