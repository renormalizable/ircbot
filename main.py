import asyncio

import client

import logging
#logging.basicConfig(level=logging.DEBUG)

loop = asyncio.get_event_loop()

bot = client.Client(loop, 'config')


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

    yield from asyncio.wait(coros)
    #asyncio.async(asyncio.wait(coros))


@asyncio.coroutine
def dump(loop):
    while True:
        #print('dump lines')
        #print(bot.lines)
        print('----- dump -----')
        all = asyncio.Task.all_tasks()
        not_done = [t for t in all if not t.done()]
        print('all: {0}, not done: {1}'.format(len(all), len(not_done)))
        for t in not_done:
            print(t)
        yield from asyncio.sleep(1)

#tasks = [bot.run(), dump(loop)]
tasks = [bot.run()]

loop.run_until_complete(asyncio.wait(tasks))
