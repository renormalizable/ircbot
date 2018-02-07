import asyncio
import tracemalloc

import client


tracemalloc.start()

loop = asyncio.get_event_loop()

bot = client.Client(loop, 'config')


@bot.on('CLIENT_CONNECT')
async def connect(**kwargs):
    bot.send('NICK', nick=bot.login)
    bot.send('PASS', password=bot.password)
    bot.send('USER', user=bot.login, realname='Bot using bottom.py')


@bot.on('PING')
async def keepalive(message, **kwargs):
    bot.send('PONG', message=message)


@bot.on('PRIVMSG')
async def privmsg_commands(nick, target, message, **kwargs):
    if nick == bot.nick:
        return
    if any(n in nick.lower() for n in ['labots']):
        return

    (nick, message) = bot.deprefix(nick, message)
    if target == bot.nick:
        sender = lambda m, **kw: bot.sender(nick, m, **kw)
    else:
        sender = lambda m, **kw: bot.sender(target, m, to=nick, **kw)

    coros = [f(bot, nick, message, sender) for f in bot.modules.commands.privmsg]

    await asyncio.wait(coros)


@bot.on('PRIVMSG')
async def privmsg_admin(nick, target, message, **kwargs):
    if target == bot.nick:
        sender = lambda m, **kw: bot.sender(nick, m, **kw)
    else:
        sender = lambda m, **kw: bot.sender(target, m, to=nick, **kw)

    coros = [f(bot, nick, message, sender) for f in bot.modules.admin.privmsg]

    await asyncio.wait(coros)


bot.loop.create_task(bot.connect())
bot.loop.run_forever()
