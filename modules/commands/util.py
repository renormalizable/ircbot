import asyncio
import re
import base64
import random


def lsend(l, send, **kw):
    #send(l, n=len(l), llimit=10)
    send(l, n=0, llimit=10, **kw)

# coreutils


@asyncio.coroutine
def echo(arg, send):
    send(arg['content'], raw=True)


@asyncio.coroutine
def cat(arg, lines, send):
    lsend(lines, send, raw=bool(arg['raw']))


@asyncio.coroutine
def tac(arg, lines, send):
    lsend(list(reversed(lines)), send)


@asyncio.coroutine
def tee(arg, lines, send):
    lsend(lines, send)
    # do not tee again?
    yield from arg['meta']['command'](arg['command'], lines, arg['meta']['send'])


@asyncio.coroutine
def head(arg, lines, send):
    l = int(arg['line'] or 10)
    lsend(lines[:l], send)


@asyncio.coroutine
def tail(arg, lines, send):
    l = int(arg['line'] or 10)
    lsend(lines[(-l):], send)


@asyncio.coroutine
def sort(arg, lines, send):
    lsend(sorted(lines), send)


@asyncio.coroutine
def uniq(arg, lines, send):
    l = lines[:1]
    for e in lines:
        if e != l[-1]:
            l.append(e)
    lsend(l, send)


@asyncio.coroutine
def b64(arg, lines, send):
    decode = arg['decode']
    content = '\n'.join(lines) or arg['content'] or ''

    if not content:
        raise Exception()

    if decode:
        lsend(base64.b64decode(content).decode('utf-8', 'replace').splitlines(), send)
    else:
        send(base64.b64encode(content.encode('utf-8')).decode('utf-8', 'replace'))


@asyncio.coroutine
def sleep(arg, lines, send):
    yield from asyncio.sleep(int(arg['time']))
    send('wake up')


@asyncio.coroutine
def wc(arg, lines, send):
    content = ('\n'.join(lines) or arg['content'] or '') + '\n'

    l = len(content.splitlines())
    w = len(content.split())
    b = len(content.encode())
    send('{0} {1} {2}'.format(l, w, b))


@asyncio.coroutine
def shuf(arg, lines, send):
    random.shuffle(lines)
    lsend(lines, send)


@asyncio.coroutine
def nl(arg, lines, send):
    for i in range(len(lines)):
        lines[i] = '{0} {1}'.format(i + 1, lines[i])
    lsend(lines, send)

# other


class Sed:

    def __init__(self):
        #self.ra = r'(?:{0}|(?P<na>\d+))'.format(r'(?:\\(?P<da>[^\\/])|/)(?P<ra>.+?)(?(da)(?P=da)|/)')
        #self.rb = r'(?:{0}|(?P<nb>\d+))'.format(r'(?:\\(?P<db>[^\\/])|/)(?P<rb>.+?)(?(db)(?P=db)|/)')
        self.ra = r'(?:(?P<na>\d+)|{0})'.format(r'(?P<a>\\)?(?P<da>(?(a)[^\\]|/))(?P<ra>.+?)(?<!\\)(?P=da)')
        self.rb = r'(?:(?P<nb>\d+)|{0})'.format(r'(?P<b>\\)?(?P<db>(?(b)[^\\]|/))(?P<rb>.+?)(?<!\\)(?P=db)')
        self.rs = r's(?P<d>[^\\])(?P<from>.*?)(?<!\\)(?P=d)(?P<to>.*?)(?<!\\)(?P=d)'
        self.rf = r'(?P<flag>.*)'
        self.reg = re.compile(r'(?:{0}(?:\s*,\s*{1})?\s*)?'.format(self.ra, self.rb) + self.rs + self.rf)
        self.addr = re.compile(r'^(?:{0}(?:\s*,\s*{1})?\s*)?'.format(self.ra, self.rb))
        self.s = re.compile(self.rs + self.rf)

    def getf(self, d):
        delimiter = d['d']
        flag = d['flag']
        rf = re.compile(d['from'].replace('\\' + delimiter, delimiter))
        rt = d['to'].replace('\\' + delimiter, delimiter)

        if flag == '':
            return lambda l: rf.sub(rt, l, count=1)
        elif flag == 'g':
            return lambda l: rf.sub(rt, l)
        else:
            raise Exception()

    def getl(self, d, lines):
        na = int(d['na']) if d['na'] else -1
        da = d['da']
        ra = re.compile(d['ra'].replace('\\' + da, da)) if d['ra'] else None
        nb = int(d['nb']) if d['nb'] else -1
        db = d['db']
        rb = re.compile(d['rb'].replace('\\' + db, db)) if d['rb'] else None

        # only a

        if not rb and nb < 0:
            if na == 0:
                return [0]
            if na > 0:
                return [(na - 1)]
            if ra:
                line = []
                for (i, l) in enumerate(lines):
                    if ra.search(l):
                        line.append(i)
                return line
            return list(range(len(lines)))

        # a and b

        if na == 0:
            na = 1
        if nb == 0:
            nb = 1

        if na > 0 and nb > 0:
            if (na - 1) < nb:
                return list(range((na - 1), nb))
            else:
                return [(na - 1)]
        if na > 0 and rb:
            for (i, l) in enumerate(lines):
                if rb.search(l):
                    break
            if (na - 1) < (i + 1):
                return list(range((na - 1), (i + 1)))
            else:
                return [(na - 1)]
        if ra and nb > 0:
            for (i, l) in enumerate(lines):
                if ra.search(l):
                    break
            if i < nb:
                return list(range(i, nb))
            else:
                return [i]
        if ra and rb:
            line = []
            inrange = False
            for (i, l) in enumerate(lines):
                if not inrange:
                    if ra.search(l):
                        inrange = True
                        line.append(i)
                else:
                    line.append(i)
                    if rb.search(l):
                        inrange = False
            return line

        return []

    @asyncio.coroutine
    def __call__(self, arg, lines, send):
        if not lines:
            raise Exception()

        script = arg['script']

        addr = self.addr.match(script)
        c = script[addr.end():] if addr else script
        comm = self.s.fullmatch(c)

        if not comm:
            raise Exception()

        da = addr.groupdict()
        dc = comm.groupdict()
        #send(da)
        #send(dc)

        f = self.getf(dc)
        tmp = lines
        for i in self.getl(da, tmp):
            tmp[i] = f(tmp[i])
        line = [l for l in tmp if l]

        lsend(line, send)

sed = Sed()


help = [
    ('echo'         , 'echo <content> -- 我才不会自问自答呢!'),
    ('cat'          , 'cat [raw] -- meow~'),
    ('base64'       , 'base64[:decode] (content)'),
]

func = [
    (echo           , r"echo (?P<content>.+)"),
    (cat            , r"cat(?:\s+(?P<raw>raw))?"),
    (tac            , r"tac"),
    (tee            , r"tee(?:\s+(?P<command>.+))?"),
    (head           , r"head(?:\s+(?P<line>\d+))?"),
    (tail           , r"tail(?:\s+(?P<line>\d+))?"),
    (sort           , r"sort"),
    (uniq           , r"uniq"),
    #(sed            , r"sed\s(?P<quote>['\"])(?P<script>.+)(?P=quote)"),
    (sed            , r"sed\s+(?P<script>.+)"),
    (b64            , r"base64(?::(?P<decode>decode))?(?:\s+(?P<content>.+))?"),
    (sleep          , r"sleep\s+(?P<time>\d+)"),
    (wc             , r"wc(?:\s+(?P<content>.+))?"),
    (shuf           , r"shuf"),
    (nl             , r"nl"),
]
