import asyncio
from urllib.parse import quote_plus, quote
from aiohttp.helpers import BasicAuth
import json
import re
import time
import base64

import romkan

from .tool import xml, jsonxml, htmlparse, jsonparse, fetch


@asyncio.coroutine
def arxiv(arg, send):
    print('arxiv')

    arg.update({
        'n': arg['n'] or '5',
        'url': 'http://export.arxiv.org/api/query',
        'xpath': arg['xpath'] or '//ns:entry',
    })
    params = {
        'search_query': arg['query'],
        'max_results': arg['n'],
        'sortBy': 'lastUpdatedDate',
        'sortOrder': 'descending',
    }
    field = [('./ns:id', 'text', '{}'), ('./ns:title', 'text', '{}')]
    def format(l):
        def f(e):
            return '[\\x0302{0}\\x0f] {1}'.format(e[0][21:], e[1].replace('\n', ' '))
        return map(f, l)

    return (yield from xml(arg, [], send, params=params, field=field, format=format))


@asyncio.coroutine
def wolfram(arg, send):
    print('wolfram')

    arg.update({
        'n': arg['n'] or '2',
        'url': 'http://api.wolframalpha.com/v2/query',
        'xpath': arg['xpath'] or '//pod',
    })
    params = {
        'appid': arg['meta']['bot'].key['wolfram'],
        'units': 'metric',
        'format': 'plaintext,image',
        #'scantimeout': '4.0',
        'input': arg['query'],
    }
    #field = [('.', 'title', '\\x0300{}:\\x0f'), ('.//plaintext', 'text', '{}')]
    field = [('.', 'title', '\\x02{}:\\x0f'), ('.//plaintext', 'text', '{}')]
    def format(l):
        #r = re.compile(r"(?<!\\)\\:([0-9a-f]{4})")
        r = re.compile(r"\\:([0-9a-f]{4})")
        def f(e):
            if e[1]:
                #return ' '.join(r.sub(lambda m: ('\\u' + m.group(1)).encode('utf-8').decode('unicode_escape'), x) for x in e)
                return ' '.join(r.sub(lambda m: chr(int(m.group(1), 16)), x) for x in e)
            else:
                return ''
        return filter(lambda x: x, map(f, l))

    return (yield from xml(arg, [], send, params=params, field=field, format=format))


@asyncio.coroutine
def ip(arg, send):
    print('ip')

    arg.update({
        'n': '1',
        'url': 'http://ip-api.com/json/' + arg['addr'],
        'xpath': '/root',
    })
    field = [('./' + x, 'text', '{}') for x in ['country', 'regionName', 'city', 'isp']]

    return (yield from jsonxml(arg, [], send, field=field))


@asyncio.coroutine
def whois(arg, send):
    print('whois')

    arg.update({
        'n': '1',
        'url': 'http://jsonwhois.com/api/v1/whois',
        'xpath': '/root',
    })
    params = {'domain': arg['domain']}
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Token token=' + arg['meta']['bot'].key['jsonwhois'],
    }
    field = [('./' + x, 'text', '{}') for x in ['status | ./status/item', 'created_on', 'updated_on']]

    return (yield from jsonxml(arg, [], send, params=params, field=field, headers=headers))


@asyncio.coroutine
def aqi(arg, send):
    print('aqi')

    arg.update({
        'n': '3',
        'url': 'http://www.pm25.in/api/querys/aqi_details.json',
        'xpath': '/root/item',
    })
    params = {
        'token': arg['meta']['bot'].key['pm25'],
        'avg': 'true',
        'stations': 'no',
        'city': arg['city'],
    }
    field = [('./' + x, 'text', '{}') for x in ['area', 'quality', 'aqi', 'primary_pollutant', 'time_point']]
    if arg.get('all'):
        l = [
            ('pm2_5', 'PM 2.5'),
            ('pm10', 'PM 10'),
            ('co', 'CO'),
            ('no2', 'NO2'),
            ('o3', 'O3'),
            ('o3_8h', 'O3 8h'),
            ('so2', 'SO2'),
        ]
        #field += [('./' + x[0], 'text', '\\x0300{0}:\\x0f'.format(x[1]) + ' {}') for x in l]
        field += [('./' + x[0], 'text', '\\x02{0}:\\x0f'.format(x[1]) + ' {}') for x in l]
        def format(l):
            e = list(l)[0]
            return [' '.join(e[:5]), ', '.join(e[5:])]
    else:
        format = None

    return (yield from jsonxml(arg, [], send, params=params, field=field, format=format))

    #@asyncio.coroutine
    #def func(byte):
    #    j = json.loads(byte.decode('utf-8'))[0]
    #    l = [' '.join(map(lambda k: str(j.get(k)), ['area', 'quality', 'aqi', 'primary_pollutant', 'time_point']))]
    #    if all:
    #        f = lambda k: '{0}: ({1} {2})'.format(k.replace('_', '.'), str(j.get(k)), str(j.get(k + '_24h')))
    #        l.append('污染物: (1h平均 24h平均)')
    #        l.append(', '.join(map(f, ['pm2_5', 'pm10', 'co', 'no2', 'o3', 'o3_8h', 'so2'])))
    #    return l

    #return (yield from fetch(url, 3, func, send))


# baidu

@asyncio.coroutine
def bip(arg, send):
    print('bip')

    url = 'http://apistore.baidu.com/microservice/'
    arg.update({
        'n': '1',
        'url': url + 'iplookup',
        'xpath': '//retData',
    })
    params = {'ip': arg['addr']}
    field = [('./' + x, 'text', '{}') for x in ['country', 'province', 'city', 'district', 'carrier']]

    return (yield from jsonxml(arg, [], send, params=params, field=field))


@asyncio.coroutine
def bid(arg, send):
    print('bid')

    url = 'http://apistore.baidu.com/microservice/'
    arg.update({
        'n': '1',
        'url': url + 'icardinfo',
        'xpath': '//retData',
    })
    params = {'id': arg['id']}
    field = [('./' + x, 'text', '{}') for x in ['sex', 'birthday', 'address']]

    return (yield from jsonxml(arg, [], send, params=params, field=field))


@asyncio.coroutine
def bphone(arg, send):
    print('bphone')

    url = 'http://apistore.baidu.com/microservice/'
    arg.update({
        'n': '1',
        'url': url + 'mobilephone',
        'xpath': '//retData',
    })
    params = {'tel': arg['tel']}
    field = [('./' + x, 'text', '{}') for x in ['telString', 'province', 'carrier']]

    return (yield from jsonxml(arg, [], send, params=params, field=field))


@asyncio.coroutine
def baqi(arg, send):
    print('baqi')

    url = 'http://apistore.baidu.com/microservice/'
    arg.update({
        'n': '1',
        'url': url + 'aqi',
        'xpath': '//retData',
    })
    params = {'city': arg['city']}
    field = [('./' + x, 'text', '{}') for x in ['city', 'level', 'aqi', 'core', 'time']]

    return (yield from jsonxml(arg, [], send, params=params, field=field))


@asyncio.coroutine
def bweather(arg, send):
    print('bweather')

    url = 'http://apistore.baidu.com/microservice/'
    arg.update({
        'n': '1',
        'url': url + 'weather',
        'xpath': '//retData',
    })
    params = {'cityname': arg['city']}
    field = [('./' + x, 'text', '{}') for x in ['city', 'weather', 'temp', 'WS', 'time', 'date']]

    return (yield from jsonxml(arg, [], send, params=params, field=field))


@asyncio.coroutine
def btran(arg, lines, send):
    print('btran')

    # we no longer use baidu translate at apistore.baidu.com
    arg.update({
        'n': '1',
        'url': 'http://openapi.baidu.com/public/2.0/bmt/translate',
        'xpath': '//trans_result/item',
    })
    params = {
        'client_id': arg['meta']['bot'].key['baidu'],
        'from': arg['from'] or 'auto',
        'to': arg['to'] or 'zh',
        'q': ' '.join(lines) or arg['text'] or '',
    }
    field = [('./dst', 'text', '{}')]

    return (yield from jsonxml(arg, [], send, params=params, field=field))


@asyncio.coroutine
def xiaodu(arg, lines, send):
    print('xiaodu')

    arg.update({
        'n': '0',
        'url': 'https://sp0.baidu.com/yLsHczq6KgQFm2e88IuM_a/s',
        'xpath': '//result_content',
    })
    params = {
        'sample_name': 'bear_brain',
        'bear_type': '2',
        # don't need login when using this
        #'plugin_uid': 'plugin_1438940543_206396858986507404845284847222447199875',
        'plugin_uid': 'plugin_1439213357_271859313658586265056880721379820623739',
        'request_time': int(time.time() * 1000),
        'request_query': arg['query'],
    }
    def transform(l):
        field = [
            ('answer', '{}'),
            ('img', '[\\x0302 {} \\x0f]'),
        ]
        def get(e):
            if e.text:
                d = jsonparse(e.text)
                l = [f[1].format(d.get(f[0])) if d.get(f[0]) else '' for f in field]
                return ' '.join(filter(any, l))
            else:
                l = e.xpath('.//answer')
                if l:
                    return e.xpath('.//answer')[0].text
                else:
                    return ''
        return map(get, l)

    return (yield from jsonxml(arg, [], send, params=params, transform=transform))


@asyncio.coroutine
def bocr(arg, send):
    print('bocr')

    if arg['url'][-3:] != 'jpg':
        return send('only support jpg...')

    (img, charset) = yield from fetch('GET', arg['url'], content='byte')

    url = 'http://apis.baidu.com/apistore/idlocr/ocr'
    arg.update({
        'url': url,
        'xpath': '//retData//word',
    })
    headers = {'apikey': arg['meta']['bot'].key['baiduocr']}
    data = {
        'fromdevice': 'pc',
        'clientip': '127.0.0.1',
        'detecttype': 'LocateRecognize',
        'languagetype': 'CHN_ENG',
        'imagetype': '1',
        'image': base64.b64encode(img).decode(),
    }
    print(data)

    return (yield from jsonxml(arg, [], send, method='POST', headers=headers, data=data))


@asyncio.coroutine
def bing(arg, lines, send):
    print('bing')

    arg.update({
        'n': arg['n'] or '1',
        'url': 'https://api.datamarket.azure.com/Bing/Search/v1/Composite',
        'xpath': '//d/results/item/Web/item',
    })
    params = {
        '$format': 'json',
        #'Sources': "'web+image+video+news+spell'",
        'Sources': "'web'",
        'Adult': "'Off'",
        'Market': "'en-US'",
        'Query': "'{0}'".format(' '.join(lines) or arg['query'] or ''),
    }
    key = arg['meta']['bot'].key['microsoft']
    auth = BasicAuth(key, key)
    field = [
        ('./Title', 'text', '{}'),
        ('./Url', 'text', '[\\x0302 {} \\x0f]'),
        ('./Description', 'text', '{}'),
    ]

    return (yield from jsonxml(arg, [], send, params=params, auth=auth, field=field))

#class Mtran(Microsoft):
#    def __init__(self):
#        super().__init__(arg['meta']['bot'].key['microsoft'], 'http://api.microsofttranslator.com', 'client_credentials')
#    @asyncio.coroutine
#    def __call__(self, arg, send):
#        print('mtran')
#        f = arg['from'] or ''
#        t = arg['to'] or 'zh-CHS'
#        url = 'http://api.microsofttranslator.com/V2/Http.svc/Translate?format=json&text={0}&from={1}&to={2}'.format(quote_plus(arg['text']), quote_plus(f), quote_plus(t))
#
#        key = yield from self.getkey()
#        headers = {'Authorization': 'Bearer ' + key}
#
#        arg['n'] = 1
#        arg['url'] = url
#        arg['xpath'] = '/ns:string'
#
#        return (yield from xml(arg, [], send, headers=headers))
#
#mtran = Mtran()


@asyncio.coroutine
def mtran(arg, lines, send):
    print('mtran')

    arg.update({
        'n': '1',
        'url': 'https://api.datamarket.azure.com/Bing/MicrosoftTranslator/v1/Translate',
        'xpath': '//d/results/item',
    })
    params = {
        '$format': 'json',
        'To': "'{0}'".format(arg['to'] or 'zh-CHS'),
        'Text': "'{0}'".format(' '.join(lines) or arg['text'] or ''),
    }
    if arg['from']:
        params['From'] = "'{0}'".format(arg['from'])
    key = arg['meta']['bot'].key['microsoft']
    auth = BasicAuth(key, key)
    field = [('./Text', 'text', '{}')]

    return (yield from jsonxml(arg, [], send, params=params, auth=auth, field=field))


@asyncio.coroutine
def couplet(arg, lines, send):
    print('couplet')

    #shanglian = arg['shanglian']
    shanglian = ' '.join(lines) or arg['shanglian'] or ''
    #if len(shanglian) > 10:
    #    send('最多十个汉字喔')
    #    return

    arg.update({
        'n': arg['n'] or '1',
        'url': 'http://couplet.msra.cn/app/CoupletsWS_V2.asmx/GetXiaLian',
        'xpath': '//d/XialianSystemGeneratedSets/item/XialianCandidates/item',
    })
    data = json.dumps({
        'shanglian': shanglian,
        'xialianLocker': '0' * len(shanglian),
        'isUpdate': False,
    })
    headers = {'Content-Type': 'application/json'}

    return (yield from jsonxml(arg, [], send, method='POST', data=data, headers=headers))


@asyncio.coroutine
def mice(arg, send):
    print('mice')
    #url = 'http://www.msxiaoice.com/v2/context'
    url = 'http://webapps.msxiaobing.com/api/simplechat/getresponse?workflow=Q20'

    input = arg['input']

    arg['n'] = '1'
    arg['url'] = url
    arg['xpath'] = '//text'

    data = json.dumps({
        'senderId': '6c54b3cf-bc0f-484e-9aee-7e00ce1c92be',
        'content': {
            'text': '开始',
            'imageUrl': ''
        }
    })
    headers = {'Content-Type': 'application/json'}

    return (yield from jsonxml(arg, [], send, method='POST', data=data, headers=headers))


# google

@asyncio.coroutine
def google(arg, lines, send):
    print('google')

    #type = arg.get('type') or 'web'
    #url = 'https://www.googleapis.com/customsearch/v1?key={0}&cx={1}&searchType={2}&q={3}'.format(quote_plus(key), quote_plus(cx), quote_plus(type), quote_plus(arg['query']))
    arg.update({
        'n': arg['n'] or '1',
        'url': 'https://www.googleapis.com/customsearch/v1',
        'xpath': '//items/item',
    })
    params = {
        'key': arg['meta']['bot'].key['google'],
        'cx': arg['meta']['bot'].key['googleseid'],
        'q': ' '.join(lines) or arg['query'] or '',
    }
    field = [
        ('./title', 'text', '{}'),
        ('./link', 'text', '[\\x0302 {} \\x0f]'),
        ('./snippet', 'text', '{}'),
    ]

    return (yield from jsonxml(arg, [], lambda m, **kw: send(m, newline=' ', **kw), params=params, field=field))

def gtrantoken(source, target, query):
    def rshift(v, n):
        if v > 0:
            return v >> n
        else:
            return (v + 0x100000000) >> n
    def rl(a, b):
        for c in range(0, len(b) - 2, 3):
            d = b[c + 2]
            # int() won't panic
            d = ord(d) - 87 if d >= 'a' else int(d)
            if b[c + 1] == '+':
                d = rshift(a, d)
            else:
                d = a << d & (2 ** 32 - 1)
                if d & 0x80000000:
                   d = d - 2 ** 32
            #print(a, d)
            a = a + d & 4294967295 if b[c] == '+' else a ^ d
        return a

    a = query
    # any better way to do this?
    #t = "{:.10f}".format(time.time() / 3600).split('.')
    #b = int(t[0])
    #c = int(t[1])
    b = 406446
    c = 626866870

    d = []
    for f in range(len(a)):
        g = ord(a[f]);

        if 128 > g:
            d.append(g)
            continue

        if 2048 > g:
            d.append(g >> 6 | 192)
        elif 55296 == (g & 64512) and f + 1 < len(a) and 56320 == (ord(a[f + 1]) & 64512):
            g = 65536 + ((g & 1023) << 10) + (ord(a[f + 1]) & 1023)
            d.append(g >> 18 | 240)
            d.append(g >> 12 & 63 | 128)
        else:
            d.append(g >> 12 | 224)
            d.append(g >> 6 & 63 | 128)

        d.append(g & 63 | 128)

    a = b
    for e in range(len(d)):
        a += d[e]
        a = rl(a, '+-a^+6')
    a = rl(a, '+-3^+b+-f')
    a ^= c
    if 0 > a:
        a = (a & 2147483647) + 2147483648
    a = int(a % 1E6)
    #print(b)
    #print(d)
    #print(str(a) + '.' + str(a ^ b))
    return str(a) + '.' + str(a ^ b)

@asyncio.coroutine
def gtran(arg, lines, send):
    print('google')

    if arg.get('to') == 'speak':
        xpath = '/root/item[1]/item/item[4]'
    elif arg.get('to') == 'lang':
        xpath = '/root/item[3]'
    else:
        xpath = '/root/item[1]/item/item[1]'

    arg.update({
        'n': '1',
        'url': 'https://translate.google.com/translate_a/single?client=t&dt=bd&dt=ex&dt=ld&dt=md&dt=qca&dt=rw&dt=rm&dt=ss&dt=t&dt=at&otf=1&ssel=0&tsel=0&kc=0',
        #'xpath': '/root/item/item/item',
        #'xpath': '/root/item[1]',
        #'xpath': '/root/item[1]/item' + ('/item[4]' if arg.get('to') == 'speak' else if '/item[1]'),
        'xpath': xpath
    })
    params = {
        'ie': 'UTF-8',
        'oe': 'UTF-8',
        'sl': arg['from'] or 'auto',
        'tl': arg['to'] or 'zh-CN',
        'hl': 'en',
        'q': ' '.join(lines) or arg['text'] or '',
        'tk': '',
    }
    params['tk'] = gtrantoken(params['sl'], params['tl'], params['q'])
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.125 Safari/537.36',
    }
    format = lambda l: [' '.join(map(lambda e: e[0], l))]

    #return (yield from jsonxml(arg, [], send, params=params, field=field, headers=headers))
    try:
        return (yield from jsonxml(arg, [], send, params=params, format=format, headers=headers))
    except:
        raise Exception("Traffic limit reached?")


@asyncio.coroutine
def dictg(arg, send):
    print('dictg')

    arg.update({
        'url': 'https://glosbe.com/gapi/translate',
        'xpath': '//tuc/item/meanings/item/text',
    })
    params = {
        'format': 'json',
        'from': arg['from'],
        'dest': arg['to'],
        'phrase': arg['text'],
    }

    return (yield from jsonxml(arg, [], send, params=params))


@asyncio.coroutine
def cdict(arg, send):
    print('cdict')

    arg.update({
        'url': 'https://api.collinsdictionary.com/api/v1/dictionaries/{0}/search/first/'.format(arg['dict'] or 'english'),
        'xpath': '//entryContent',
    })
    params = {'format': 'html', 'q': arg['text']}
    headers = {'accessKey': arg['meta']['bot'].key['collins']}
    transform = lambda l: htmlparse(l[0].text).xpath('//span[@class = "pos"] | //span[@class = "def"]')

    return (yield from jsonxml(arg, [], send, params=params, transform=transform, headers=headers))


@asyncio.coroutine
def urban(arg, send):
    print('urban')

    # unofficial
    arg.update({
        'n': arg['n'] or '1',
        'url': 'https://mashape-community-urban-dictionary.p.mashape.com/define',
        'xpath': '//list/item',
    })
    params = {'term': arg['text']}
    headers = {'X-Mashape-Key': arg['meta']['bot'].key['mashape']}
    field = [
        ('./definition', 'text', '{}'),
        #('./permalink', 'text', '[\\x0302 {} \\x0f]'),
    ]

    return (yield from jsonxml(arg, [], send, params=params, field=field, headers=headers))


@asyncio.coroutine
def breezo(arg, send):
    print('breezo')

    arg.update({
        'n': '1',
        'url': 'http://api-beta.breezometer.com/baqi/',
        'xpath': '/root',
    })
    params = {'key': arg['meta']['bot'].key['breezo'], 'location': arg['city']}
    field = [('./' + x, 'text', '{}') for x in ['breezometer_description', 'breezometer_aqi', 'dominant_pollutant_text/main', 'random_recommendations/health']]

    return (yield from jsonxml(arg, [], send, params=params, field=field))


@asyncio.coroutine
def speak(arg, send):
    print('speak')

    arg.update({
        'n': '1',
        'url': 'http://howtospeak.org:443/api/e2c',
        'xpath': '//chinglish',
    })
    params = {
        'user_key': arg['meta']['bot'].key['howtospeak'],
        'notrans': '0',
        'text': arg['text'],
    }

    return (yield from jsonxml(arg, [], send, params=params))


@asyncio.coroutine
def watson(arg, send):
    pass

help = [
    ('ip'           , 'ip <ip address>'),
    #('whois'        , 'whois <domain>'),
    ('aqi'          , 'aqi <city> [all]'),
    #('bip'          , 'bip <ip address>'),
    #('bweather'     , 'bweather <city>'),
    #('btran'        , 'btran [source lang:target lang] (text)'),
    #('xiaodu'       , 'xiaodu <query>'),
    #('bing'         , 'bing <query> [#max number][+offset]'),
    ('bing'         , 'bing (query) [#max number][+offset]'),
    #('bing'         , 'bing [#max number][+offset] (query)'),
    ('mtran'        , 'mtran [source lang:target lang] (text)'),
    #('couplet'      , 'couplet <shanglian (max ten chinese characters)> [#max number][+offset] -- 公门桃李争荣日 法国荷兰比利时'),
    #('couplet'      , 'couplet <shanglian> [#max number][+offset] -- 公门桃李争荣日 法国荷兰比利时'),
    ('couplet'      , 'couplet (shanglian) [#max number][+offset] -- 公门桃李争荣日 法国荷兰比利时'),
    #('google'       , 'google <query> [#max number][+offset]'),
    ('google'       , 'google (query) [#max number][+offset]'),
    #('google'       , 'google [#max number][+offset] (query)'),
    ('gtran'        , 'gtran [source lang:target lang] (text)'),
    ('urban'        , 'urban <text> [#max number][+offset]'),
    ('speak'        , 'speak <text>'),
    ('wolfram'      , 'wolfram <query> [#max number][+offset]'),
]

func = [
    (ip             , r"ip\s+(?P<addr>.+)"),
    (whois          , r"whois\s+(?P<domain>.+)"),
    (aqi            , r"aqi\s+(?P<city>.+?)(\s+(?P<all>all))?"),
    #(bip            , r"bip\s+(?P<addr>.+)"),
    #(bid            , r"bid\s+(?P<id>.+)"),
    #(bphone         , r"bphone\s+(?P<tel>.+)"),
    #(baqi           , r"baqi\s+(?P<city>.+)"),
    #(bweather       , r"bweather\s+(?P<city>.+)"),
    #(btran          , r"btran(\s+(?!:\s)(?P<from>\S+)?:(?P<to>\S+)?)?\s+(?P<text>.+)"),
    #(btran          , r"btran(\s+(?!:\s)(?P<from>\S+)?:(?P<to>\S+)?)?(\s+(?P<text>.+))?"),
    (xiaodu         , r"xiaodu\s+(?P<query>.+)"),
    (bocr           , r"bocr\s+(?P<url>http.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(bing           , r"bing(\s+type:(?P<type>\S+))?\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (bing           , r"bing(?:\s+(?![#\+])(?P<query>.+?))?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(bing           , r"bing(\s+type:(?P<type>\S+))?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?(\s+(?P<query>.+))?"),
    #(mtran          , r"mtran(\s+(?!:\s)(?P<from>\S+)?:(?P<to>\S+)?)?\s+(?P<text>.+)"),
    (mtran          , r"mtran(\s+(?!:\s)(?P<from>\S+)?:(?P<to>\S+)?)?(\s+(?P<text>.+))?"),
    #(couplet        , r"couplet\s+(?P<shanglian>\S+)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (couplet        , r"couplet(?:\s+(?P<shanglian>\S+))?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(mice           , r"mice\s+(?P<input>.+)"),
    #(google         , r"google(\s+type:(?P<type>(web|image)))?\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(google         , r"google\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (google         , r"google(?:\s+(?![#\+])(?P<query>.+?))?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(google         , r"google(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?(\s+(?P<query>.+))?"),
    (gtran          , r"gtran(\s+(?!:\s)(?P<from>\S+)?:(?P<to>\S+)?)?(\s+(?P<text>.+))?"),
    (dictg          , r"dict\s+(?P<from>\S+):(?P<to>\S+)\s+(?P<text>.+?)(\s+#(?P<n>\d+))?"),
    (cdict          , r"collins(\s+d:(?P<dict>\S+))?\s+(?P<text>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (breezo         , r"breezo\s+(?P<city>.+)"),
    (speak          , r"speak\s+(?P<text>.+)"),
    (urban          , r"urban\s+(?P<text>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (urban          , r"rural\s+(?P<text>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(arxiv          , r"arxiv\s+(?P<query>.+?)(\s+xpath:(?P<xpath>.+?))?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (wolfram        , r"wolfram\s+(?P<query>.+?)(\s+xpath:(?P<xpath>.+?))?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
]
