import asyncio
import tracemalloc

import client


tracemalloc.start()

bot = client.Client('config')


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
    #if nick == bot.nick:
    #    return
    #if 'condy' in nick.lower() or 'flandre' in nick.lower() or 'youmu' in nick.lower():
    #    return
    #if '#linux-cn' == target:
    #    return
    if any(n in nick.lower() for n in ['labots']):
        return

    (nick, message) = bot.deprefix(nick, message)
    if target == bot.nick:
        sender = lambda m, **kw: bot.sender(nick, m, **kw)
    else:
        sender = lambda m, **kw: bot.sender(target, m, to=nick, **kw)

    coros = [f(bot, nick, message, sender) for f in bot.modules.commands.privmsg]

    await asyncio.wait([asyncio.create_task(c) for c in coros])


@bot.on('PRIVMSG')
async def privmsg_admin(nick, target, message, **kwargs):
    if target == bot.nick:
        sender = lambda m, **kw: bot.sender(nick, m, **kw)
    else:
        sender = lambda m, **kw: bot.sender(target, m, to=nick, **kw)

    coros = [f(bot, nick, message, sender) for f in bot.modules.admin.privmsg]

    await asyncio.wait([asyncio.create_task(c) for c in coros])


bot.loop.create_task(bot.connect())
bot.loop.run_forever()
