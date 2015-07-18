import asyncio
import re
import time
from urllib.parse  import quote_plus
from aiohttp       import request
from colorsys      import rgb_to_hsv

from .common import Get
from .tool import fetch, htmltostr, html, xml, addstyle, jsonparse, htmlparse


@asyncio.coroutine
def moegirl(arg, send):
    print('moegirl')

    # apply function before addstyle()
    # \x0f should be the last character before tail
    def hidden(e):
        for b in e.xpath('.//b'):
            b.text = '\\x0300' + (b.text or '')
            b.tail = '\\x0f' + (b.tail or '')
        for span in e.xpath('.//span[@class="heimu"]'):
            span.text = '\\x0301' + (span.text or '')
            span.tail = '\\x0f' + (span.tail or '')
        return e

    arg.update({
        'url': 'http://zh.moegirl.org/api.php',
        'xpath': '//rev',
    })
    params = {
        'format': 'xml',
        'action': 'query',
        'generator': 'search',
        'gsrlimit': '1',
        'gsrsearch': arg['query'],
        'prop': 'revisions',
        'rvprop': 'content',
        'rvparse': '',
    }
    transform = lambda l: htmlparse(l[0].text).xpath('//body/*[not(self::div or self::table or self::h2)]')
    get = lambda e, f: addstyle(hidden(e)).xpath('string()')

    return (yield from xml(arg, [], send, params=params, transform=transform, get=get))


@asyncio.coroutine
def nmb(arg, send):
    print('nmb')
    #url = 'http://h.koukuko.com/'
    #url = 'http://kukuku.cc/'
    url = 'http://h.nimingban.com/'
    #url = 'http://hacfun.tv/'

    if arg['id']:
        arg.update({
            'url': url + 't/{0}'.format(arg['id']),
            'xpath': '//div[@id="h-content"]/div[1]/div[3]/div[1] | //div[@id="h-content"]/div[1]/div[3]/div[1]/div[2]/div',
        })
        if arg['show']:
            send('[\\x0302 {} \\x0f]'.format(arg['url']))
    else:
        arg.update({
            'url': url + (arg['forum'] or '综合版1'),
            'xpath': '//div[@id="h-content"]/div[1]/div[3]/div',
        })
    field = [
        ('.', 'data-threads-id', '[\\x0304{}\\x0f]'),
        ('./div[re:test(@class, "main$")]/div[@class="h-threads-content"]', '', '{}'),
        ('./div[re:test(@class, "main$")]/div[@class="h-threads-img-box"]/a', 'href', '[\\x0302 {} \\x0f]'),
    ]

    return (yield from html(arg, [], send, field=field))


@asyncio.coroutine
def adnmb(arg, send):
    print('adnmb')
    url = 'http://h.adnmb.com/home/forum/'

    if arg['id']:
        arg.update({
            'url': url + 'thread/id/{0}/page/1.html'.format(arg['id']),
            'xpath': '//div[@id="threads"]/div',
        })
        if arg['show']:
            send(arg['url'])
    else:
        arg.update({
            'url': url + 'showt/id/{0}.html'.format(arg['forum'] or '1'),
            'xpath': '//div[@id="threads"]/div[@class="threadpost"]',
        })
    field = [
        ('.', 'id', '[\\x0304{}\\x0f]'),
        ('.//div[@class="quote"]', '', '{}'),
        ('.//img', 'src', '[\\x0302 http://h.adnmb.com{} \\x0f]'),
    ]

    return (yield from html(arg, [], send, field=field))


#@asyncio.coroutine
#def acfun(arg, send):
#    print('acfun')
#    count = int(arg['count'])
#    url = 'http://www.acfun.tv/comment_list_json.aspx?contentId={0}&currentPage='.format(quote_plus(arg['id']))
#
#    def ubb(s):
#        # color inside b, i, u will cause problem
#        # nested tag not handled
#        table = [
#            (r"\[size=\S+?\](.*?)\[\/size\]"                           , r"\1"),
#            #(r"\[s\](.*?)\[\/s\]"                                      , r"\1"),
#            (r"\[at\](.*?)\[\/at\]"                                    , r"\x0300@\1\x0f"),
#            (r"\[img=\S+?\](.*?)\[\/img\]"                             , r"[\x0302 \1 \x0f]"),
#            (r"\[ac=\S+?\](.*?)\[\/ac\]"                               , r"[\x0302 http://www.acfun.tv/v/\1 \x0f]"),
#            (r"\[b\](.*?)\[\/b\]"                                      , r"\x02\1\x02"),
#            (r"\[i\](.*?)\[\/i\]"                                      , r"\x1d\1\x1d"),
#            (r"\[u\](.*?)\[\/u\]"                                      , r"\x1f\1\x1f"),
#            #(r"\[color=#(?!00)[0-9a-zA-Z]{2}0000\](.*?)\[\/color\]"    , r"\x0304\1\x0f"),
#            #(r"\[color=#00(?!00)[0-9a-zA-Z]{2}00\](.*?)\[\/color\]"    , r"\x0303\1\x0f"),
#            #(r"\[color=#0000(?!00)[0-9a-zA-Z]{2}\](.*?)\[\/color\]"    , r"\x0302\1\x0f"),
#            #(r"\[color=#[fF]{6}\](.*?)\[\/color\]"                     , r"\x0301\1\x0f"),
#        ]
#        colorreg = re.compile(r"\[color=#(?P<r>[0-9a-zA-Z]{2})(?P<g>[0-9a-zA-Z]{2})(?P<b>[0-9a-zA-Z]{2})\](?P<text>.*?)\[\/color\]")
#        convert = {
#            0: '05',
#            1: '08',
#            2: '03',
#            3: '10',
#            4: '02',
#            5: '06',
#            6: '05',
#        }
#        def color(m):
#            d = m.groupdict()
#            text = d['text']
#            r = int(d['r'], 16) / 255.0
#            g = int(d['g'], 16) / 255.0
#            b = int(d['b'], 16) / 255.0
#
#            (h, s, v) = rgb_to_hsv(r, g, b)
#
#            hshift = (h + 1.0 / 12)
#            hshift = hshift - 1.0 if hshift >= 1.0 else hshift
#            color = int(hshift * 6)
#
#            return '\x03{0}{1}\x0f'.format(convert[color], text)
#
#        for (r, f) in table:
#            s = re.sub(r, f, s)
#        s = colorreg.sub(color, s)
#        return s
#
#    @asyncio.coroutine
#    def func(num):
#        text = yield from fetch('GET', url + str(num))
#        j = jsonparse(text)
#        # or branch is for older comment format
#        d = j.get('commentContentArr') or j.get('data').get('commentContentArr')
#        try:
#            while True:
#                e = d.popitem()[1]
#                if e.get('count') == count:
#                    return ['\\x0300{0}:\\x0f {1}'.format(e.get('userName'), ubb(htmltostr(e.get('content'))))]
#        except KeyError:
#            n = j.get('totalPage')
#            i = j.get('page')
#            if i >= n:
#                raise Exception()
#            else:
#                return (yield from func(i + 1))
#
#    line = yield from func(1)
#    return send(line, n=1)

class Acfun:

    def __init__(self):
        self.reg = re.compile(r"\[(?P<type>\S+?)(?:=(?P<args>\S+?))?\](?P<text>.*?)\[\/(?P=type)\]")
        # color inside b, i, u will cause problem
        self.table = {
            'size':     lambda a, t: t,
            #'s':        lambda a, t: t,
            'at':       lambda a, t: r"\x0300@{0}\x0f".format(t),
            'img':      lambda a, t: r"[\x0302 {0} \x0f]".format(t),
            'ac':       lambda a, t: r"[\x0302 http://www.acfun.tv/v/{0} \x0f]".format(t),
            'b':        lambda a, t: r"\x02{0}\x02".format(t),
            'i':        lambda a, t: r"\x1d{0}\x1d".format(t),
            'u':        lambda a, t: r"\x1f{0}\x1f".format(t),
            'color':    self.color,
        }
        self.colorreg = re.compile(r"#(?P<r>[0-9a-zA-Z]{2})(?P<g>[0-9a-zA-Z]{2})(?P<b>[0-9a-zA-Z]{2})")
        self.convert = {
            0: '05',
            1: '08',
            2: '03',
            3: '10',
            4: '02',
            5: '06',
            6: '05',
        }

    def color(self, a, t):
        d = self.colorreg.fullmatch(a).groupdict()
        r = int(d['r'], 16) / 255.0
        g = int(d['g'], 16) / 255.0
        b = int(d['b'], 16) / 255.0

        (h, s, v) = rgb_to_hsv(r, g, b)

        hshift = (h + 1.0 / 12)
        hshift = hshift - 1.0 if hshift >= 1.0 else hshift
        color = int(hshift * 6)

        return r"\x03{0}{1}\x0f".format(self.convert[color], t)

    def dispatch(self, m):
        d = m.groupdict()
        #print(d)
        type = d['type']
        args = d['args']
        text = d['text']

        f = self.table.get(type) or (lambda a, t: "<{0}>{1}<\{0}>".format(type, text))
        return f(args, text)

    def ubb(self, s):
        t = time.time()
        n = 1
        # handle badly nested tags
        while n > 0:
            (s, n) = self.reg.subn(self.dispatch, s)
        print('ubb time:', time.time() - t)
        return s

    @asyncio.coroutine
    def func(self, url, num, count):
        text = yield from fetch('GET', url + str(num))
        j = jsonparse(text)
        # or branch is for older comment format
        d = j.get('commentContentArr') or j.get('data').get('commentContentArr')
        try:
            while True:
                e = d.popitem()[1]
                if e.get('count') == count:
                    return ['\\x0300{0}:\\x0f {1}'.format(e.get('userName'), self.ubb(htmltostr(e.get('content'))))]
        except KeyError:
            n = j.get('totalPage')
            i = j.get('page')
            if i >= n:
                raise Exception()
            else:
                return (yield from self.func(url, i + 1, count))

    @asyncio.coroutine
    def __call__(self, arg, send):
        print('acfun')
        count = int(arg['count'])
        url = 'http://www.acfun.tv/comment_list_json.aspx?contentId={0}&currentPage='.format(quote_plus(arg['id']))

        line = yield from self.func(url, 1, count)
        return send(line, n=1)

acfun = Acfun()

help = [
    ('moegirl'      , 'moegirl <title> [#max number][+offset]'),
    ('nmb'          , 'nmb [fforum] [thread id] [#max number][+offset] -- 丧失你好'),
    #('adnmb'        , 'adnmb [fforum id] [rthread id] [#max number][+offset] -- 丧失你好'),
    ('acfun'        , 'acfun [acpage id] <#comment number>'),
]

func = [
    (moegirl        , r"moegirl\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (nmb            , r"nmb(\s+f(?P<forum>\S+))?(\s+(?P<id>\d+))?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?(\s+(?P<show>show))?"),
    (adnmb          , r"adnmb(\s+f(?P<forum>\d+))?(\s+r(?P<id>\d+))?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?(\s+(?P<show>show))?"),
    (acfun          , r"acfun\s+ac(?P<id>\d+)\s+#(?P<count>\d+)"),
]
