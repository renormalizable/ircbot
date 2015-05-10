import asyncio
import re

def lsend(l, send):
    send(l, n=len(l), llimit=10)

# coreutils

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
def tac(arg, lines, send):
    if not lines:
        raise Exception()

    lsend(list(reversed(lines.splitlines())), send)

@asyncio.coroutine
def tee(arg, lines, send):
    if not lines:
        raise Exception()

    line = lines.splitlines()
    lsend(line)

@asyncio.coroutine
def head(arg, lines, send):
    if not lines:
        raise Exception()

    lsend(lines.splitlines()[:10], send)

@asyncio.coroutine
def tail(arg, lines, send):
    if not lines:
        raise Exception()

    lsend(lines.splitlines()[-10:], send)

@asyncio.coroutine
def sort(arg, lines, send):
    if not lines:
        raise Exception()

    lsend(sorted(lines.splitlines()), send)

@asyncio.coroutine
def uniq(arg, lines, send):
    if not lines:
        raise Exception()

    line = lines.splitlines()
    l = [line[0]]
    for e in line:
        if e != l[-1]:
            l.append(e)
    lsend(l, send)

# other

class Sed:
    def __init__(self):
        self.ra = r'(?:{0}|(?P<na>\d+))'.format(r'(?:\\(?P<da>[^\\/])|/)(?P<ra>.+?)(?(da)(?P=da)|/)')
        self.rb = r'(?:{0}|(?P<nb>\d+))'.format(r'(?:\\(?P<db>[^\\/])|/)(?P<rb>.+?)(?(db)(?P=db)|/)')
        self.rs = r's(?P<d>[^\\])(?P<from>.*?)(?<!\\)(?P=d)(?P<to>.*?)(?<!\\)(?P=d)'
        self.rf = r'(?P<flag>.*)'
        self.reg = re.compile(r'(?:{0}(?:\s*,\s*{1})?\s*)?'.format(self.ra, self.rb) + self.rs + self.rf)

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
        da = d['da'] or '/'
        ra = re.compile(d['ra'].replace('\\' + da, da)) if d['ra'] else None
        na = int(d['na']) if d['na'] else -1
        db = d['db'] or '/'
        rb = re.compile(d['rb'].replace('\\' + db, db)) if d['rb'] else None
        nb = int(d['nb']) if d['nb'] else -1

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

        command = self.reg.fullmatch(arg['script'])

        if not command:
            raise Exception()

        d = command.groupdict()
        #send(d)

        f = self.getf(d)
        line = lines.splitlines()
        result = []
        print(self.getl(d, result))
        for i in self.getl(d, line):
            l = f(line[i])
            if l:
                result.append(l)

        lsend(result, send)

sed = Sed()

help = [
    ('echo'         , 'echo <content> -- 我才不会自问自答呢!'),
    ('cat'          , 'cat [raw] -- meow~'),
]

func = [
    (echo           , r"echo (?P<content>.*)"),
    (cat            , r"cat(\s+(?P<raw>raw))?"),
    (tac            , r"tac"),
    (head           , r"head"),
    (tail           , r"tail"),
    (sort           , r"sort"),
    (uniq           , r"uniq"),
    (sed            , r"sed\s(?P<quote>['\"])(?P<script>.*)(?P=quote)"),
]
