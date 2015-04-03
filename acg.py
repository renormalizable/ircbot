import asyncio
import re
from urllib.parse  import quote_plus
from aiohttp       import request

from tool import fetch, htmltostr, html, addstyle, jsonparse

@asyncio.coroutine
def moegirl(arg, send):
    print('moegirl')
    n = int(arg['n']) if arg['n'] else 5
    url = 'http://zh.moegirl.org/' + quote_plus(arg['query'])

    # apply function before addstyle()
    # \x0f should be the last character before tail
    def hidden(e):
        for b in e.xpath('.//b'):
            b.text = '\\x0300' + b.text if b.text else '\\x0300'
            b.tail = '\\x0f' + b.tail if b.tail else '\\x0f'
        for span in e.xpath('.//span[@class="heimu"]'):
            span.text = '\\x0301' + span.text if span.text else '\\x0301'
            span.tail = '\\x0f' + span.tail if span.tail else '\\x0f'
        return e

    arg['n'] = n
    arg['url'] = url
    arg['xpath'] = '//*[@id="mw-content-text"]/p'
    get = lambda e, f: addstyle(hidden(e)).xpath('string()')

    return (yield from html(arg, send, get=get))

    #url = 'http://zh.moegirl.org/api.php?format=json&action=query&prop=revisions&rvprop=content&rvgeneratexml&titles=' + quote_plus(arg['query'])

    #@asyncio.coroutine
    #def func(byte):
    #    j = json.loads(byte.decode('utf-8'))
    #    d = j.get('query').get('pages').popitem()[1]
    #    t = d.get('revisions')[0].get('parsetree')
    #    print(t)
    #    return [', '.join(map(lambda x: str(x), [j.get('breezometer_description'), j.get('breezometer_aqi'), j.get('dominant_pollutant_text').get('main'), j.get('random_recommendations').get('health')]))]

    #return (yield from fetch(url, 1, func, send))

@asyncio.coroutine
def nmb(arg, send):
    print('nmb')
    n = int(arg['n']) if arg['n'] else 5
    url = 'http://h.koukuko.com/'

    arg['n'] = n
    if arg['id']:
        arg['url'] = url + 't/{0}'.format(arg['id'])
        arg['xpath'] = '//div[@id="h-content"]/div[1]/div[3]/div[1] | //div[@id="h-content"]/div[1]/div[3]/div[1]/div[2]/div'
        if arg['show']:
            send('[\\x0302{}\\x0f]'.format(arg['url']))
    else:
        forum = arg['forum'] or '综合版1'
        arg['url'] = url + forum
        arg['xpath'] = '//div[@id="h-content"]/div[1]/div[3]/div'
    #field = [('.', 'data-threads-id', '[\\x0304{}\\x0f]'), ('./div[re:test(@class, "main$")]/div[@class="h-threads-content"]', 'text_content', '{}'), ('./div[re:test(@class, "main$")]/div[@class="h-threads-img-box"]/a', 'href', '[\\x0302{}\\x0f]')]
    field = [('.', 'data-threads-id', '[\\x0304{}\\x0f]'), ('./div[re:test(@class, "main$")]/div[@class="h-threads-content"]', 'text_content', '{}'), ('./div[re:test(@class, "main$")]/div[@class="h-threads-img-box"]/a', 'href', '\\x0302{} \\x0f')]
    #field = [('.', 'data-threads-id', '[\\x0304{}\\x0f]'), ('./div[re:test(@class, "main$")]/div[@class="h-threads-content"]', 'text_content', '{}'), ('./div[re:test(@class, "main$")]/div[@class="h-threads-img-box"]/a', 'href', '{}')]
    #format = lambda l: map(lambda e: ' '.join([e[0], e[1], '[\\x0302{}\\x0f]'.format(e[2][7:]) if e[2] else '']), l)

    #return (yield from html(arg, send, field=field, format=format))
    return (yield from html(arg, send, field=field))

@asyncio.coroutine
def adnmb(arg, send):
    print('adnmb')
    n = int(arg['n']) if arg['n'] else 5
    url = 'http://h.adnmb.com/home/forum/'

    arg['n'] = n
    if arg['id']:
        arg['url'] = url + 'thread/id/{0}/page/1.html'.format(arg['id'])
        arg['xpath'] = '//div[@id="threads"]/div'
        if arg['show']:
            send(arg['url'])
    else:
        forum = arg['forum'] or '1'
        arg['url'] = url + 'showt/id/{0}.html'.format(forum)
        arg['xpath'] = '//div[@id="threads"]/div[@class="threadpost"]'
    field = [('.', 'id', '[\\x0304{}\\x0f]'), ('.//div[@class="quote"]', 'text_content', '{}'), ('.//img', 'src', '[\\x0302http://h.adnmb.com{}\\x0f]')]

    return (yield from html(arg, send, field=field))

@asyncio.coroutine
def acfun(arg, send):
    print('acfun')
    count = int(arg['count'])
    url = 'http://www.acfun.tv/comment_list_json.aspx?contentId={0}&currentPage='.format(quote_plus(arg['id']))

    def ubb(s):
        # color inside b, i, u will cause problem
        # nested tag not handled
        table = [
            (r"\[size=\S+?\](.*?)\[\/size\]"                           , r"\1"),
            #(r"\[s\](.*?)\[\/s\]"                                     , r"\1"),
            (r"\[at\](.*?)\[\/at\]"                                    , r"\x0300@\1\x0f"),
            (r"\[img=\S+?\](.*?)\[\/img\]"                             , r"[\x0302\1\x0f]"),
            (r"\[ac=\S+?\](.*?)\[\/ac\]"                               , r"[\x0302http://www.acfun.tv/v/\1\x0f]"),
            (r"\[b\](.*?)\[\/b\]"                                      , r"\x02\1\x02"),
            (r"\[i\](.*?)\[\/i\]"                                      , r"\x1d\1\x1d"),
            (r"\[u\](.*?)\[\/u\]"                                      , r"\x1f\1\x1f"),
            (r"\[color=#(?!00)[0-9a-zA-Z]{2}0000\](.*?)\[\/color\]"    , r"\x0304\1\x0f"),
            (r"\[color=#00(?!00)[0-9a-zA-Z]{2}00\](.*?)\[\/color\]"    , r"\x0303\1\x0f"),
            (r"\[color=#0000(?!00)[0-9a-zA-Z]{2}\](.*?)\[\/color\]"    , r"\x0302\1\x0f"),
        ]
        for (r, f) in table:
            s = re.sub(r, f, s)
        return s

    @asyncio.coroutine
    def func(byte):
        j = jsonparse(byte)
        # or is for older comment format
        d = j.get('commentContentArr') or j.get('data').get('commentContentArr')
        try:
            while True:
                e = d.popitem()[1]
                if e.get('count') == count:
                    #return [', '.join([e.get('userName'), ubb(htmltostr(e.get('content')))])]
                    return ['\\x0300{0}:\\x0f {1}'.format(e.get('userName'), ubb(htmltostr(e.get('content'))))]
        except KeyError:
            n = j.get('totalPage')
            i = j.get('page')
            if i >= n:
                raise Exception()
            else:
                r = yield from request('GET', url + str(i + 1))
                b = yield from r.read()
                return (yield from func(b))

    return (yield from fetch('GET', url + '1', 1, func, send))

help = {
    'moegirl'        : 'moegirl <title> [#max number]',
    'nmb'            : 'nmb [fforum] [thread id] [#max number] -- 丧失你好',
    'adnmb'          : 'adnmb [fforum id] [rthread id] [#max number] -- 丧失你好',
    'acfun'          : 'acfun [acpage id] <#comment number>',
}

func = [
    (moegirl,         r"moegirl\s+(?P<query>.+?)(\s+#(?P<n>\d+))?"),
    (nmb,             r"nmb(\s+f(?P<forum>\S+))?(\s+(?P<id>\d+))?(\s+#(?P<n>\d+))?(\s+(?P<show>show))?"),
    (adnmb,           r"adnmb(\s+f(?P<forum>\d+))?(\s+r(?P<id>\d+))?(\s+#(?P<n>\d+))?(\s+(?P<show>show))?"),
    (acfun,           r"acfun\s+ac(?P<id>\d+)\s+#(?P<count>\d+)"),
]
