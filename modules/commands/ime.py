import asyncio
from urllib.parse import quote
from aiohttp.client import ClientRequest
import re

# no kwa wha etc.
# find an alternative?
import romkan

from .tool import jsonxml


@asyncio.coroutine
def kana(arg, send):
    send(romkan.to_hiragana(arg['romaji']))


@asyncio.coroutine
def romaji(arg, send):
    send(romkan.to_roma(arg['kana']))


class IM:

    class Getter:

        def __init__(self):
            self.l = ''
            self.len = 0

        def __call__(self, l, n=-1, **kw):
            if n < 0:
                self.l += l
            else:
                l = list(l)[0]
                print(l)
                self.l += l[0]
                self.len = int(l[1] or 0)

    def __init__(self, Getter=None):
        self.prefix = "'"
        self.sep = re.compile(r"([^a-z']+)")
        self.valid = re.compile(r"[a-z']")
        self.letter = re.compile(r"[^']")
        self.comment = re.compile(r"(?:(?<=[^a-z'])|^)''(.*?)''(?:(?=[^a-z'])|$)")
        self.Get = Getter or IM.Getter

    def special(self, e):
        return e[1:]

    @asyncio.coroutine
    def request(self, e, get):
        pass

    def getpos(self, e, l):
        pass

    @asyncio.coroutine
    def process(self, e):
        get = self.Get()
        while len(e) > 0:
            #print(e)
            yield from self.request(e, get)
            pos = self.getpos(e, get.len)
            e = e[pos:]
        return get.l

    @asyncio.coroutine
    def getitem(self, e):
        if not self.valid.match(e):
            return e
        if e[0] == self.prefix:
            return self.special(e)

        return (yield from self.process(e))

    @asyncio.coroutine
    def __call__(self, input, send):
        print('im')

        l = []
        pos = 0
        for m in self.comment.finditer(input):
            l.extend(self.sep.split(input[pos:m.start()]))
            #l.append("'" + m.group()[2:-2])
            l.append(m.group()[1:-2])
            pos = m.end()
        l.extend(self.sep.split(input[pos:]))
        #l = self.sep.split(input)
        print(l)

        coros = [self.getitem(e) for e in l]
        lines = yield from asyncio.gather(*coros)
        line = ''.join(lines) if lines else 'Σ(っ °Д °;)っ 怎么什么都没有呀'

        return send(line)


class BIM(IM):

    def __init__(self):
        IM.__init__(self)
        self.arg = {
            'n': '1',
            'url': 'http://olime.baidu.com/py',
            'xpath': '//result/item[1]/item[child::item]',
        }
        self.params = {
            'inputtype': 'py',
            'bg': '0',
            'ed': '5',
            'result': 'hanzi',
            'resultcoding': 'unicode',
            'ch_en': '0',
            'clientinfo': 'web',
            'version': '1',
            'input': '',
        }
        self.field = [('./item[1]', 'text', '{}'), ('./item[2]', 'text', '{}')]
        self.format = lambda x: x

    @asyncio.coroutine
    def request(self, e, get):
        params = self.params.copy()
        params['input'] = e
        yield from jsonxml(self.arg, [], get, params=params, field=self.field, format=self.format)

    def getpos(self, e, l):
        if not (0 < l and l < len(e)):
            return len(e)
        for (i, c) in enumerate(self.letter.finditer(e)):
            if i == l:
                return c.start()
        return len(e)

    @asyncio.coroutine
    def __call__(self, arg, send):
        yield from IM.__call__(self, arg['pinyin'], send)

bim = BIM()


class IMNEW:

    class Getter:

        def __init__(self):
            self.l = ''
            self.len = 0

        def __call__(self, l, n=-1, **kw):
            if n < 0:
                self.l += l
            else:
                l = list(l)[0]
                print(l)
                self.l += l[0]
                self.len = int(l[1] or 0)

    def __init__(self, Getter=None):
        self.Get = Getter or IMNEW.Getter

    @asyncio.coroutine
    def request(self, e, get):
        pass

    def getpos(self, e, l):
        pass

    @asyncio.coroutine
    def process(self, e):
        get = self.Get()
        while len(e) > 0:
            #print(e)
            yield from self.request(e, get)
            pos = self.getpos(e, get.len)
            e = e[pos:]
        return get.l

    @asyncio.coroutine
    def getitem(self, e):
        if e[0]:
            return (yield from self.process(e[1]))
        else:
            return e[1]

    @asyncio.coroutine
    def __call__(self, input, send):
        print('im')

        coros = [self.getitem(e) for e in input]
        lines = yield from asyncio.gather(*coros)
        line = ''.join(lines) if lines else 'Σ(っ °Д °;)っ 怎么什么都没有呀'
        print(line)

        return send(line)


class GIMNEW(IMNEW):

    # our url does not conform with url standard
    class RequestGoogle(ClientRequest):

        def __init__(self, method, url, *, params=None, **kw):
            ClientRequest.__init__(self, method, url, params=params, **kw)
            # note the extra quote for ','
            if params:
                #p = '&'.join('='.join((i[0], i[1].replace(',', quote(quote(','))))) for i in params.items())
                #self.url._val = self.url._val._replace(query=p)
                p = [(i[0], i[1].replace(',', quote(quote(',')))) for i in params.items()]
                self.url = url.with_query(p).with_fragment(None)

    def __init__(self, itc):
        IMNEW.__init__(self)
        self.arg = {
            'n': '1',
            'url': 'https://inputtools.google.com/request',
            # is always well formed?
            'xpath': '/root/item[2]/item[1]',
        }
        self.params = {
            'itc': itc,
            'num': '1',
            'cp': '0',
            'cs': '0',
            'ie': 'utf-8',
            'oe': 'utf-8',
            'app': 'demopage',
            'text': '',
        }
        self.field = [
            ('./item[2]/item[1]', 'text', '{}'),
            ('./item[3]/item[1]', 'text', '{}'),
        ]
        self.format = lambda x: x

    @asyncio.coroutine
    def request(self, e, get):
        params = self.params.copy()
        params['text'] = e
        yield from jsonxml(self.arg, [], get, method='POST', params=params, request_class=GIMNEW.RequestGoogle, field=self.field, format=self.format)

    def getpos(self, e, l):
        if not (0 < l and l < len(e)):
            return len(e)
        return l

    @asyncio.coroutine
    def __call__(self, input, send):
        yield from IMNEW.__call__(self, input, send)


@asyncio.coroutine
def gimnew(arg, send):
    print('gimnew')

    table = {
        # pinyin
        'pinyins':          'zh-t-i0-pinyin',
        'pinyint':          'zh-hant-t-i0-pinyin',
        # wubi
        'wubi':             'zh-t-i0-wubi-1986',
        # shuangpin
        'shuangpinabc':     'zh-t-i0-pinyin-x0-shuangpin-abc',
        'shuangpinms':      'zh-t-i0-pinyin-x0-shuangpin-ms',
        'shuangpinflypy':   'zh-t-i0-pinyin-x0-shuangpin-flypy',
        'shuangpinjiajia':  'zh-t-i0-pinyin-x0-shuangpin-jiajia',
        'shuangpinziguang': 'zh-t-i0-pinyin-x0-shuangpin-ziguang',
        'shuangpinziranma': 'zh-t-i0-pinyin-x0-shuangpin-ziranma',
        # zhuyin
        'zhuyin':           'zh-hant-t-i0-und',
        # for blackberry layout
        'zhuyinbb':         'zh-hant-t-i0-und',
        # cangjie
        'cangjie':          'zh-hant-t-i0-cangjie-1982',
        # yue
        'yue':              'yue-hant-t-i0-und',
        # ja
        'ja':               'ja-t-ja-hira-i0-und',
    }
    alias = {
        # default
        'chs':              'pinyins',
        'cht':              'pinyint',
        'pinyin':           'pinyins',
        'shuangpin':        'shuangpinflypy',
        # alias
        'ggtt':             'wubi',
        'vtpc':             'shuangpinabc',
        'udpn':             'shuangpinms',
        'ulpb':             'shuangpinflypy',
        'ihpl':             'shuangpinjiajia',
        'igpy':             'shuangpinziguang',
        'udpnzrm':          'shuangpinziranma',
        '5j4up=':           'zhuyin',
        'rhnyoo$':          'zhuyinbb',
        'oiargrmbc':        'cangjie',
        'yut':              'yue',
    }

    def parse(reg, text, f, g):
        line = []
        pos = 0
        for m in reg.finditer(text):
            line.extend(f(text[pos:m.start()]))
            line.extend(g(m.group()))
            pos = m.end()
        line.extend(f(text[pos:]))

        return line

    def replace(text, rule):
        if not rule:
            return text
        (f, t) = rule[0]
        parts = text.split(f)
        return t.join(replace(part, rule[1:]) for part in parts)

    try:
        lang = arg['lang'] or 'chs'
        lang = alias.get(lang, lang)
        itc = table[lang]
    except:
        #raise Exception("this method is not supported yet...")
        raise Exception("Do you REALLY need this input method?")

    if lang == 'zhuyin':
        sep = re.compile(r"([^a-z'0-9\-;,./=]+)")
        comment = re.compile(r"(?:(?<=[^a-z'0-9\-;,./=])|^)''(.*?)''(?:(?=[^a-z'0-9\-;,./=])|$)")
    elif lang == 'zhuyinbb':
        sep = re.compile(r"([^a-z'0$]+)")
        comment = re.compile(r"(?:(?<=[^a-z'0$])|^)''(.*?)''(?:(?=[^a-z'0$])|$)")
    elif lang == 'ja':
        sep = re.compile(r"([^a-z'\-]+)")
        comment = re.compile(r"(?:(?<=[^a-z'\-])|^)''(.*?)''(?:(?=[^a-z'\-])|$)")
    else:
        sep = re.compile(r"([^a-z']+)")
        comment = re.compile(r"(?:(?<=[^a-z'])|^)''(.*?)''(?:(?=[^a-z'])|$)")

    text = arg['text']

    line = parse(comment, text,
        lambda t: parse(sep, t,
            #lambda x: [(True, e) for e in x.split("'")] if x != '' and x[0].islower() else [(False, x)],
            # for zhuyin
            lambda x: [(True, e) for e in x.split("'")] if x != '' else [(False, x)],
            lambda x: [(False, x)]
        ),
        lambda t: [(False, t[2:-2])]
    )

    if lang == 'ja':
        tmp = []
        for e in line:
            if e[0]:
                tmp.append((e[0], romkan.to_hiragana(e[1])))
            else:
                tmp.append(e)
        line = tmp
    elif lang == 'zhuyinbb':
        tmp = []
        for e in line:
            if e[0]:
                t = [
                    ('aa', 'z'),
                    ('dd', 'f'),
                    ('ee', 'r'),
                    ('ii', 'o'),
                    ('jj', ','),
                    ('kk', '.'),
                    ('ll', '/'),
                    ('oo', 'p'),
                    ('qq', 'q'),
                    ('rr', 't'),
                    ('ss', 'x'),
                    ('uu', 'i'),
                    ('ww', 'w'),
                    ('xx', 'v'),
                    ( 'a', 'a'),
                    ( 'b', 'm'),
                    ( 'c', 'b'),
                    ( 'd', 'd'),
                    ( 'e', 'e'),
                    ( 'f', 'g'),
                    ( 'g', 'h'),
                    ( 'h', 'j'),
                    ( 'i', '9'),
                    ( 'j', 'k'),
                    ( 'k', 'l'),
                    ( 'l', ';'),
                    ( 'm', '7'),
                    ( 'n', '4'),
                    ( 'o', '0'),
                    ( 'p', '-'),
                    ( 'q', '1'),
                    ( 'r', '5'),
                    ( 's', 's'),
                    ( 't', 'y'),
                    ( 'u', '8'),
                    ( 'v', 'n'),
                    ( 'w', '2'),
                    ( 'x', 'c'),
                    ( 'y', 'u'),
                    ( 'z', '6'),
                    ( '0', '3'),
                    ( '$', '='),
                ]
                tmp.append((e[0], replace(e[1], t)))
            else:
                tmp.append(e)
        line = tmp
    print(line)

    im = GIMNEW(itc)
    yield from im(line, send)


class BIMNEW(IMNEW):

    def __init__(self):
        IMNEW.__init__(self)
        self.arg = {
            'n': '1',
            'url': 'http://olime.baidu.com/py',
            'xpath': '//result/item[1]/item[child::item]',
        }
        self.params = {
            'inputtype': 'py',
            'bg': '0',
            'ed': '5',
            'result': 'hanzi',
            'resultcoding': 'unicode',
            'ch_en': '0',
            'clientinfo': 'web',
            'version': '1',
            'input': '',
        }
        self.field = [('./item[1]', 'text', '{}'), ('./item[2]', 'text', '{}')]
        self.format = lambda x: x

    @asyncio.coroutine
    def request(self, e, get):
        params = self.params.copy()
        params['input'] = e
        yield from jsonxml(self.arg, [], get, params=params, field=self.field, format=self.format)

    def getpos(self, e, l):
        if not (0 < l and l < len(e)):
            return len(e)
        for (i, c) in enumerate(self.letter.finditer(e)):
            if i == l:
                return c.start()
        return len(e)

    @asyncio.coroutine
    def __call__(self, input, send):
        yield from IMNEW.__call__(self, input, send)


@asyncio.coroutine
def bimnew(arg, send):
    print('bimnew')

    def parse(reg, text, f, g):
        line = []
        pos = 0
        for m in reg.finditer(text):
            line.extend(f(text[pos:m.start()]))
            line.extend(g(m.group()))
            pos = m.end()
        line.extend(f(text[pos:]))

        return line

    def replace(text, rule):
        if not rule:
            return text
        (f, t) = rule[0]
        parts = text.split(f)
        return t.join(replace(part, rule[1:]) for part in parts)

    sep = re.compile(r"([^a-z']+)")
    comment = re.compile(r"(?:(?<=[^a-z'])|^)''(.*?)''(?:(?=[^a-z'])|$)")

    text = arg['text']

    line = parse(comment, text,
        lambda t: parse(sep, t,
            lambda x: [(True, e) for e in x.split("'")] if x != '' else [(False, x)],
            lambda x: [(False, x)]
        ),
        lambda t: [(False, t[2:-2])]
    )
    print(line)

    im = BIMNEW()
    yield from im(line, send)


help = [
    ('bim'          , 'bim <pinyin> (a valid pinyin starts with a lower case letter, followed by lower case letters or \'; use \'\' in pair for comment)'),
    ('gim'          , 'gim[:lang] <text> (a valid text consists some lower case letters and other symbols; use \' for word breaking; use \'\' in pair for comment)'),
    #('kana'         , 'kana <romaji>'),
    #('romaji'       , 'romaji <kana>'),
]

func = [
    #(bim            , r"bim\s+(?P<pinyin>.+)"),
    (bimnew         , r"bim\s+(?P<text>.+)"),
    (gimnew         , r"gim(?::(?P<lang>\S+))?\s+(?P<text>.+)"),
    (kana           , r"kana\s+(?P<romaji>.+)"),
    (romaji         , r"romaji\s+(?P<kana>.+)"),
]
