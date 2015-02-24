import asyncio
import json
from urllib.parse  import quote_plus
from aiohttp       import request

from tool import fetch, htmltostr, html


#@asyncio.coroutine
#def moegirl(arg, send):
#    print('moegirl')
#    url = 'http://zh.moegirl.org/api.php?format=json&action=query&prop=revisions&rvprop=content&rvgeneratexml&titles=' + quote_plus(arg['query'])
#
#    @asyncio.coroutine
#    def func(byte):
#        j = json.loads(byte.decode('utf-8'))
#        d = j.get('query').get('pages').popitem()[1]
#        t = d.get('revisions')[0].get('parsetree')
#        print(t)
#        return [', '.join(map(lambda x: str(x), [j.get('breezometer_description'), j.get('breezometer_aqi'), j.get('dominant_pollutant_text').get('main'), j.get('random_recommendations').get('health')]))]
#
#    return (yield from fetch(url, 1, func, send))

@asyncio.coroutine
def nmb(arg, send):
    print('nmb')
    n = int(arg['n']) if arg['n'] else 5
    url = 'http://h.adnmb.com/home/forum/'

    arg['n'] = n
    arg['format'] = None
    if arg['id']:
        arg['url'] = url + 'thread/id/{0}/page/1.html'.format(arg['id'])
        arg['xpath'] = '//div[@id="threads"]/div'
        field = [('.', 'id', '[\x0304{}\x0f]'), ('.//div[@class="quote"]', 'text_content', '{}'), ('.//img', 'src', '<\x0302http://h.adnmb.com{}\x0f>')]
        if arg['show']:
            send(arg['url'])
    else:
        forum = arg['forum'] or '1'
        arg['url'] = url + 'showt/id/{0}.html'.format(forum)
        arg['xpath'] = '//div[@id="threads"]/div[@class="threadpost"]'
        field = [('.', 'id', '[\x0304{}\x0f]'), ('./div[@class="quote"]', 'text_content', '{}'), ('.//img', 'src', '<\x0302http://h.adnmb.com{}\x0f>')]

    return (yield from html(arg, send, field=field))

@asyncio.coroutine
def acfun(arg, send):
    print('acfun')
    count = int(arg['count'])
    url = 'http://www.acfun.tv/comment_list_json.aspx?contentId={0}&currentPage='.format(quote_plus(arg['id']))

    @asyncio.coroutine
    def func(byte):
        j = json.loads(byte.decode('utf-8'))
        d = j.get('commentContentArr').values()
        e = next((x for x in d if x.get('count') == count), None)
        if e:
            return [', '.join([e.get('userName'), htmltostr(e.get('content'))])]
        else:
            n = j.get('totalPage')
            i = j.get('page')
            if i >= n:
                raise Exception()
            else:
                r = yield from request('GET', url + str(i + 1))
                b = yield from r.read()
                return (yield from func(b))

    return (yield from fetch(url + '1', 1, func, send))

help = {
    'nmb'            : 'nmb [#forum id] [rthread id] [max number] -- 丧失你好',
    'acfun'          : 'acfun [acpage id] <#comment number>',
}

func = [
    #(moegirl,         r"moegirl\s+(?P<query>.+)"),
    (nmb,             r"nmb(\s+#(?P<forum>\d+))?(\s+r(?P<id>\d+))?(\s+(?P<n>\d+))?(\s+(?P<show>show))?"),
    (acfun,           r"acfun\s+ac(?P<id>\d+)\s+#(?P<count>\d+)"),
]
