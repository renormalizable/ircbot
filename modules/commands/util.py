import asyncio

def lsend(l, send):
    send(l, n=len(l), llimit=10)

@asyncio.coroutine
def echo(arg, send):
    send(arg['content'], raw=True)

@asyncio.coroutine
def cat(arg, lines, send):
    if not lines:
        raise Exception()

    if arg['raw']:
        send(lines, raw=True)
    else:
        lsend(lines.splitlines(), send)

@asyncio.coroutine
def sort(arg, lines, send):
    lsend(sorted(lines.splitlines()), send)

help = [
    ('echo'         , 'echo <content> -- 我才不会自问自答呢!'),
    ('cat'          , 'cat [raw] -- meow~'),
]

func = [
    (echo           , r"echo (?P<content>.*)"),
    (cat            , r"cat(\s+(?P<raw>raw))?"),
    (sort           , r"sort"),
]
