import asyncio
import re
import base64
import random
from .common import Get


def lsend(l, send, **kw):
    #send(l, n=len(l), llimit=10)
    send(l, n=0, llimit=10, **kw)


async def cmdsub(cmd, string):
    print('cmdsub')

    #esc = [
    #    # irssi
    #    # https://github.com/irssi/irssi/blob/master/src/fe-common/core/formats.c#L1086
    #    # IS_COLOR_CODE(...)
    #    # https://github.com/irssi/irssi/blob/master/src/fe-common/core/formats.c#L1254
    #    # format_send_to_gui(...)
    #    (r'\x02', '\x02'),
    #    (r'\x03', '\x03'),
    #    (r'\x04', '\x04'),
    #    (r'\x06', '\x06'),
    #    (r'\x07', '\x07'),
    #    (r'\x0f', '\x0f'),
    #    (r'\x16', '\x16'),
    #    (r'\x1b', '\x1b'),
    #    (r'\x1d', '\x1d'),
    #    (r'\x1f', '\x1f'),
    #]

    async def identity(x):
        return x

    # how about normalizing the message?
    async def command(x):
        get = Get()
        status = await cmd(x, [], get)
        if status:
            #msg = get.str(sep=' ')
            #for (s, e) in esc:
            #    msg = msg.replace(s, e)
            #return msg
            #return get.str(sep=' ')
            return get.str()
        else:
            return '({0})'.format(x)

    def splitter(s):
        i = 0
        j = 0
        n = 0
        while i < len(s):
            if s[i] == '(':
                n = n + 1
                if n == 1:
                    yield s[j:i]
                    j = i + 1
            elif s[i] == ')':
                n = n - 1
                if n == 0:
                    yield s[j:i]
                    j = i + 1
            i = i + 1
        if n != 0:
            raise Exception()
        else:
            yield s[j:i]


    #reg = re.compile(r"''(.*?)''")
    #reg = re.compile(r"\((.*?)\)")
    #s = reg.split(string)
    try:
        s = list(splitter(string))
    except:
        print('unmatched parentheses: {0}'.format(repr(string)))
        return string

    coros = [command(x) if i % 2 == 1 else identity(x) for (i, x) in enumerate(s)]
    s = await asyncio.gather(*coros)
    print('cmdsub: {0}'.format(s))

    return ''.join(s)


async def lower(arg, send):
    send(arg['content'].lower())


async def upper(arg, send):
    send(arg['content'].upper())


async def newline(arg, send):
    send('\n\n')


# coreutils


async def echo(arg, send):
    send(arg['content'], raw=True)


async def cat(arg, lines, send):
    lsend(lines, send, raw=bool(arg['raw']))


async def tac(arg, lines, send):
    lsend(list(reversed(lines)), send)


async def tee(arg, lines, send):
    lsend(lines, send)
    # do not tee again?
    if arg['output'] == '\'':
        await arg['meta']['command'](arg['command'], lines, arg['meta']['send'])
    if arg['output'] == '"':
        await arg['meta']['command'](arg['command'], lines, arg['meta']['save'])


async def head(arg, lines, send):
    l = int(arg['line'] or 10)
    lsend(lines[:l], send)


async def tail(arg, lines, send):
    l = int(arg['line'] or 10)
    lsend(lines[(-l):], send)


async def sort(arg, lines, send):
    lsend(sorted(lines), send)


async def uniq(arg, lines, send):
    l = lines[:1]
    for e in lines:
        if e != l[-1]:
            l.append(e)
    lsend(l, send)


async def b64(arg, lines, send):
    decode = arg['decode']
    content = '\n'.join(lines) or arg['content'] or ''

    if not content:
        raise Exception()

    if decode:
        lsend(base64.b64decode(content).decode('utf-8', 'replace').splitlines(), send)
    else:
        send(base64.b64encode(content.encode('utf-8')).decode('utf-8', 'replace'))


async def sleep(arg, lines, send):
    await asyncio.sleep(int(arg['time']))
    send('wake up')


async def wc(arg, lines, send):
    content = ('\n'.join(lines) or arg['content'] or '') + '\n'

    l = len(content.splitlines())
    w = len(content.split())
    b = len(content.encode())
    send('{0} {1} {2}'.format(l, w, b))


async def shuf(arg, lines, send):
    random.shuffle(lines)
    lsend(lines, send)


async def nl(arg, lines, send):
    for i in range(len(lines)):
        lines[i] = '{0} {1}'.format(i + 1, lines[i])
    lsend(lines, send)


async def paste(arg, lines, send):
    lsend([(arg['delimiter'] or '\n').join(lines)], send)


async def tr(arg, lines, send):
    line = [arg['content']] if arg['content'] else lines
    lsend([l.replace(arg['old'], arg['new']) for l in line], send)

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

    async def __call__(self, arg, lines, send):
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
    #(echo           , r"echo (?P<content>.+)"),
    (cat            , r"cat(?:\s+(?P<raw>raw))?"),
    (tac            , r"tac"),
    (tee            , r"tee(?:\s+(?P<output>['\"])(?P<command>.+))?"),
    (head           , r"head(?:\s+(?P<line>\d+))?"),
    (tail           , r"tail(?:\s+(?P<line>\d+))?"),
    (sort           , r"sort"),
    (uniq           , r"uniq"),
    #(sed            , r"sed\s(?P<quote>['\"])(?P<script>.+)(?P=quote)"),
    (sed            , r"sed\s+(?P<script>.+)"),
    (b64            , r"base64(?::(?P<decode>decode))?(?:\s+(?P<content>.+))?"),
    #(sleep          , r"sleep\s+(?P<time>\d+)"),
    (wc             , r"wc(?:\s+(?P<content>.+))?"),
    (shuf           , r"shuf"),
    (nl             , r"nl"),
    (paste          , r"paste(?:\s+(?P<quote>['\"])(?P<delimiter>.+)(?P=quote))?"),
    (tr             , r"tr\s+(?P<quote1>['\"])(?P<old>.+)(?P=quote1)\s+(?P<quote2>['\"])(?P<new>.*)(?P=quote2)(?:\s(?P<content>.+))?"),
    #(lower          , r"lower (?P<content>.+)"),
    #(upper          , r"upper (?P<content>.+)"),
    #(newline        , r"newline"),
    #(newline        , r"lf"),
]
