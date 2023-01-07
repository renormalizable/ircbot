import asyncio

import toxclient

loop = asyncio.get_event_loop()

bot = toxclient.ToxClient(loop, 'config.json', 'config')


@bot.on('tox.init')
def init(this, arguments):
    print("ID: {}".format(this.core.self_get_address()))

@bot.on('tox.connect')
def status(this, arguments):
    print("{} to Tox Network.".format(arguments.get('status')))

@bot.on('friend.status')
def friend_status(this, arguments):
    target = arguments.get('target')
    status = arguments.get('status')

    nick = this.get_nick(target)
    info = "Online" if status else "Offline"

    print("{} is {}.".format(nick, info))

@bot.on('friend.request')
def friend_request(this, arguments):
    print("friend request, {} {}".format(
        arguments.get('pk'),
        arguments.get('message')
    ))
    this.core.friend_add_norequest(arguments.get('pk'))

@bot.on('group.invite')
def group_invite(this, arguments):
    group = this.core.join_groupchat(
        arguments.get('target'),
        arguments.get('data')
    )
    print("Invited to group {}", group)

@bot.on('friend.message')
def friend_message(this, arguments):
    target = arguments.get('target')
    message = arguments.get('message')
    nick = this.get_nick(target)

    sender = lambda m, **kw: bot.sender(target, m, command='friend', **kw)

    coros = [f(bot, nick, message, sender) for f in bot.modules.table['commands'].privmsg]

    return (await asyncio.wait(coros))

@bot.on('group.message.normal')
def group_message(this, arguments):
    target = arguments.get('target')
    peer = arguments.get('peer')
    message = arguments.get('message')
    nick = this.group_get_nick(target, peer)

    if message.startswith('@@ '):
        message = message[3:]
    else:
        return

    (nick, message) = bot.deprefix(nick, message)

    sender = lambda m, **kw: bot.sender(target, m, to=('@@ ' + nick), command='group', **kw)

    coros = [f(bot, nick, message, sender) for f in bot.modules.table['commands'].privmsg]

    return (await asyncio.wait(coros))

tasks = [bot.run()]

if __name__ == '__main__':
    #try:
    #    loop.run_until_complete(asyncio.wait(tasks))
    #except KeyboardInterrupt:
    #    bot.save()
    while True:
        try:
            loop.run_until_complete(asyncio.wait(tasks))
        except KeyboardInterrupt:
            bot.save()
        except:
            pass
