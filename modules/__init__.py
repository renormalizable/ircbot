import importlib
import asyncio

path = 'modules.'
files = ['commands']
modules = [importlib.reload(importlib.import_module(path + f)) for f in files]

reply = modules[0].reply
fetch = modules[0].fetch

@asyncio.coroutine
def multiline(bot, nick, message, send):
    if message[:4] == "'.. " or message == "'..":
        print('multiline')
        l = [message[4:].rstrip()]
        bot.addlines(nick, l)

@asyncio.coroutine
def fetchline(bot, nick, message, send):
    if message[:4] == "':: ":
        print('fetchline')
        try:
            l = yield from fetch(message[4:].rstrip())
            bot.addlines(nick, l)
        except:
            send("出错了啦...")
            raise


@asyncio.coroutine
def reload(bot, nick, message, send):
    if nick != bot.admin or message != "'!reload":
        return

    print('reload')
    try:
        bot.reload()
        send('reloaded')
    except:
        send('error')
        raise

privmsg = [
    reply,
    multiline,
    fetchline,
    reload,
]
