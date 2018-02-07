import asyncio
import itertools
import traceback
import tracemalloc


async def reload(bot, nick, message, send):
    if nick != bot.admin or message != "'!reload":
        return

    try:
        bot.reload()
        send('reloaded')
    except:
        trace = traceback.format_exc()
        print(trace)
        trace = trace.splitlines()
        send('error: traceback {} lines'.format(len(trace)))
        if len(trace) > 10:
            send('...')
        send(trace[-10:], n=0, stripspace=False)


async def status(bot, nick, message, send):
    if nick != bot.admin or message != "'!status":
        return

    tasks = asyncio.Task.all_tasks()
    running = [t for t in tasks if not t.done()]
    done = [t for t in tasks if t.done()]
    send('tasks: total {}, running {}'.format(len(tasks), len(running)))
    send(itertools.chain(
        ('+ {}'.format(t) for t in running),
        ('- {}'.format(t) for t in done)
    ), n=10)

    snapshot = tracemalloc.take_snapshot()
    top = snapshot.statistics('lineno')
    send('memeory: total {} KiB'.format(sum(stat.size for stat in top) / 1024))
    send(top, n=10)


#async def dump(loop):
#    while True:
#        #print('dump lines')
#        #print(bot.lines)
#        print('----- dump -----')
#        all = asyncio.Task.all_tasks()
#        not_done = [t for t in all if not t.done()]
#        print('all: {0}, not done: {1}'.format(len(all), len(not_done)))
#        for t in all:
#            print('task:', t, gc.get_referrers(t))
#        print('gc:', gc.garbage, gc.get_stats())
#        try:
#            snapshot = tracemalloc.take_snapshot()
#            top = snapshot.statistics('lineno')
#            for stat in top[:10]:
#                print(stat)
#            total = sum(stat.size for stat in top)
#            print("Total allocated size: %.1f KiB" % (total / 1024))
#        except Exception as e:
#            print(e)
#        await asyncio.sleep(10)
