import asyncio

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

func = [
    (reload         , r"reload"),
]
