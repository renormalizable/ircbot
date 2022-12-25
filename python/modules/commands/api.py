import asyncio
from urllib.parse import quote, quote_plus, urlencode
from aiohttp.helpers import BasicAuth
import json
import re
import time
import random
import base64
import datetime
import socket
import codecs
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA

from .tool import xml, jsonxml, htmlparse, jsonparse, fetch


# TODO https://dictionaryapi.com/
# TODO https://pokeapi.co/


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

    try:
        #addr = socket.inet_ntop(socket.AF_INET, socket.inet_pton(socket.AF_INET, arg['addr']))
        addr = socket.inet_ntoa(socket.inet_aton(arg['addr']))
    except:
        try:
            addr = socket.inet_ntop(socket.AF_INET6, socket.inet_pton(socket.AF_INET6, arg['addr']))
        except:
            #raise Exception('illegal IP address')
            addr = arg['addr']

    arg.update({
        'n': '1',
        'url': 'http://ip-api.com/json/' + addr,
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


# see also http://www.cnemc.cn/sssj/ and http://www.cnemc.cn/getIndexData.do
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
            ('pm2_5', 'PM 2.5 1h', 'µg/m³'),
            ('pm10', 'PM 10 1h', 'µg/m³'),
            ('co', 'CO 1h', 'mg/m³'),
            ('no2', 'NO₂ 1h', 'µg/m³'),
            ('o3', 'O₃ 1h', 'µg/m³'),
            ('o3_8h', 'O₃ 8h', 'µg/m³'),
            ('so2', 'SO₂ 1h', 'µg/m³'),
        ]
        field += [('./' + x[0], 'text', '\\x02{0}:\\x0f {{}} {1}'.format(x[1], x[2])) for x in l]
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


# microsoft
# azure portal needs phone number

class Microsoft:
    class Get:
        def __init__(self):
            self.key = ''
            self.expire = 0
        def __call__(self, l, n=-1, **kw):
            e = list(l)[0]
            self.key = e[0]
            self.expire = int(e[1])
    def __init__(self, scope, type):
        self.arg = {
            'url': 'https://datamarket.accesscontrol.windows.net/v2/OAuth2-13',
            'xpath': '/root',
        }
        self.field = [('./access_token', 'text', '{}'), ('./expires_in', 'text', '{}')]
        self.format = lambda x: x
        self.headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        self.data = {
            'client_id': '',
            'client_secret': '',
            'scope': scope,
            'grant_type': type,
        }
        self.key = ''
        self.time = 0
        self.expire = 0
    def setclient(self, client):
        self.data['client_id'] = client[0]
        self.data['client_secret'] = client[1]
    @asyncio.coroutine
    def getkey(self):
        t = time.time()
        if (t - self.time) > self.expire:
            yield from self.renew()
        return self.key
    @asyncio.coroutine
    def renew(self):
        get = Microsoft.Get()
        yield from jsonxml(self.arg, [], get, method='POST', data=self.data, headers=self.headers, field=self.field, format=self.format)
        self.time = time.time()
        self.expire = get.expire - 60
        self.key = get.key

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

class Mtran(Microsoft):
    def __init__(self):
        super().__init__('http://api.microsofttranslator.com', 'client_credentials')
    @asyncio.coroutine
    def __call__(self, arg, lines, send):
        print('mtran')

        arg.update({
            'n': '1',
            'url': 'http://api.microsofttranslator.com/V2/Http.svc/Translate',
            'xpath': '/ns:string',
        })
        params = {
            'format': 'json',
            'from': arg['from'] or '',
            'to': arg['to'] or 'zh-CHS',
            'text': ' '.join(lines) or arg['text'] or '',
        }

        self.setclient(arg['meta']['bot'].key['translator'])
        key = yield from self.getkey()
        headers = {'Authorization': 'Bearer ' + key}

        return (yield from xml(arg, [], send, params=params, headers=headers))

mtran = Mtran()


# not working as of 20190611
@asyncio.coroutine
def couplet(arg, lines, send):
    print('couplet')

    #shanglian = arg['shanglian']
    shanglian = ''.join(lines) or arg['shanglian'] or ''
    #if len(shanglian) > 10:
    #    send('最多十个汉字喔')
    #    return

    if re.search(r"[\x00-\xFF、。，．：；？！]", shanglian) is not None:
        raise Exception('only chinese characters are allowed')

    arg.update({
        'n': arg['n'] or '1',
        #'url': 'https://couplet.msra.cn/app/CoupletsWS_V2.asmx/GetXiaLian',
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
            a = a + d & 4294967295 if b[c] == '+' else a ^ d
        return a

    a = query
    b = 417661
    c = 1724234313

    # js charCodeAt
    l = []
    for i in a:
        if ord(i) <= 0xffff:
            l.append(ord(i))
        else:
            encode = i.encode('utf-16-le')
            l.append(int.from_bytes(encode[:2], 'little'))
            l.append(int.from_bytes(encode[2:], 'little'))

    # generate d
    d = []
    f = 0
    while f < len(l):
        g = l[f]

        if 128 > g:
            d.append(g)
        else:
            if 2048 > g:
                d.append(g >> 6 | 192)
            else:
                if 55296 == (g & 64512) and f + 1 < len(l) and 56320 == (l[f + 1] & 64512):
                    g = 65536 + ((g & 1023) << 10) + (l[f + 1] & 1023)
                    f = f + 1
                    d.append(g >> 18 | 240)
                    d.append(g >> 12 & 63 | 128)
                else:
                    d.append(g >> 12 | 224)
                d.append(g >> 6 & 63 | 128)
            d.append(g & 63 | 128)
        f = f + 1

    a = b
    for e in range(len(d)):
        a += d[e]
        a = rl(a, '+-a^+6')
    a = rl(a, '+-3^+b+-f')
    a ^= c
    if 0 > a:
        a = (a & 2147483647) + 2147483648
    a = int(a % 1E6)

    return str(a) + '.' + str(a ^ b)

@asyncio.coroutine
def gtran(arg, lines, send):
    print('google')

    alias = {
        'jp': 'ja',
        'zh': 'zh-CN',
        'zhs': 'zh-CN',
        'zht': 'zh-TW',
    }

    lang_from = arg.get('from')
    lang_to = arg.get('to')
    # alias
    lang_from = alias.get(lang_from, lang_from)
    lang_to = alias.get(lang_to, lang_to)

    if lang_to and lang_to.startswith('audio'):
        if lang_from == None:
            raise Exception('please specify input language')

        speed = re.fullmatch(r"audio:([0-9.]+)", lang_to)

        #url = 'https://translate.google.com/translate_tts?client=t&prev=input&total=1&idx=0'
        url = 'https://translate.google.com/translate_tts?total=1&idx=0&client=webapp'
        params = {
            'ie': 'UTF-8',
            'tl': lang_from,
            'q': ' '.join(lines) or arg['text'] or '',
            'textlen': '',
            'ttsspeed': speed.group(1) if speed else '1.0',
            'tk': '',
        }
        # textlen should not larger than 200
        # TODO we need to do splitting
        params['textlen'] = len(params['q'])
        params['tk'] = gtrantoken('', params['tl'], params['q'])
        url = url + '&' + urlencode(params)

        if params['textlen'] > 200:
            raise Exception('input is toooooooooo long')

        #arg.update({
        #    'n': '1',
        #    'url': 'https://www.googleapis.com/urlshortener/v1/url?key=' + arg['meta']['bot'].key['google'],
        #    'xpath': '/root/id',
        #})
        #data = json.dumps({
        #    'longUrl': url,
        #})
        #headers = {'Content-Type': 'application/json'}
        #field = [
        #    ('.', '', '[\\x0302 {} \\x0f] (-lisa)'),
        #]

        #return (yield from jsonxml(arg, [], send, method='POST', data=data, headers=headers, field=field))
        return send('[\\x0302 {} \\x0f]'.format(url))

    if lang_to == 'speak':
        xpath = '/root/item[1]/item/item[4]'
    elif lang_to == 'lang':
        xpath = '/root/item[3]'
    else:
        xpath = '/root/item[1]/item/item[1]'

    arg.update({
        'n': '1',
        #'url': 'https://translate.google.com/translate_a/single?client=t&dt=at&dt=bd&dt=ex&dt=ld&dt=md&dt=qca&dt=rw&dt=rm&dt=ss&dt=t&otf=1&ssel=0&tsel=0&kc=0',
        'url': 'https://translate.google.com/translate_a/single?client=webapp&dt=at&dt=bd&dt=ex&dt=ld&dt=md&dt=qca&dt=rw&dt=rm&dt=sos&dt=ss&dt=t&dt=gt&source=bh&ssel=0&tsel=0&kc=1',
        #'xpath': '/root/item/item/item',
        #'xpath': '/root/item[1]',
        #'xpath': '/root/item[1]/item' + ('/item[4]' if lang_to == 'speak' else if '/item[1]'),
        'xpath': xpath,
    })
    params = {
        'ie': 'UTF-8',
        'oe': 'UTF-8',
        'sl': lang_from or 'auto',
        'tl': lang_to or 'zh-CN',
        'hl': 'en',
        'q': ' '.join(lines) or arg['text'] or '',
        'tk': '',
    }
    params['tk'] = gtrantoken(params['sl'], params['tl'], params['q'])
    # workaround https://github.com/aio-libs/aiohttp/issues/1901
    params['q'] = params['q'].replace(';', quote(quote(';')))
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
    # see https://github.com/NightfallAlicorn/urban-dictionary
    arg.update({
        'n': arg['n'] or '1',
        #'url': 'https://mashape-community-urban-dictionary.p.mashape.com/define',
        'url': 'https://api.urbandictionary.com/v0/define',
        'xpath': '//list/item',
    })
    params = {'term': arg['text']}
    #headers = {'X-Mashape-Key': arg['meta']['bot'].key['mashape']}
    field = [
        ('./definition', 'text', '{}'),
        #('./permalink', 'text', '[\\x0302 {} \\x0f]'),
    ]

    #return (yield from jsonxml(arg, [], send, params=params, field=field, headers=headers))
    return (yield from jsonxml(arg, [], send, params=params, field=field))


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


# see core.js window.asrsea funtion, AES CBC
def music163encrypt(string):
    def ran(n):
        b = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        c = ''
        for i in range(0, n):
            c = c + random.choice(b)
        return c
    def aes(a, b):
        key = b
        iv = b'0102030405060708'
        # pkcs7 padding
        pad = len(key) - len(a) % len(key)
        text = a + (pad * chr(pad)).encode()

        cipher = AES.new(key, AES.MODE_CBC, iv)
        return base64.b64encode(cipher.encrypt(text))
    def rsa(a, b, c):
        # from https://github.com/darknessomi/musicbox
        text = a
        pubKey = b
        modulus = c
        text = text[::-1]
        rs = int(codecs.encode(text, 'hex_codec'), 16) ** int(pubKey, 16) % int(modulus, 16)
        return format(rs, 'x').zfill(256).encode()

    # e f g are constants
    d = string.encode()
    e = b'010001'
    f = b'00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7'
    g = b'0CoJUm6Qyw8W8jud'
    i = ran(16).encode()
    i = b'0000000000000000'

    encText = aes(d, g)
    encText = aes(encText, i)
    encSecKey = rsa(i, e, f)

    data = {
        'params': encText.decode(),
        'encSecKey': encSecKey.decode(),
    }

    return data


@asyncio.coroutine
def music163(arg, send):
    print('music163')

    query = arg['query']

    if arg['type'] == 'song' or arg['type'] == None:
        ty = '1'
        xpath = '//result/songs/item'
        field = [
            ('./name', '', '{}'),
            ('./id', '', '[\\x0302 https://music.163.com/song?id={} \\x0f]'),
            ('./artists//name', '', 'by {}'),
            ('./album/name', '', 'in {}'),
            ('./duration', '', '{}'),
        ]
        def formatter(e):
            name = e[0]
            url = e[1]
            artist = e[2]
            album = e[3]
            duration = datetime.timedelta(seconds=int(e[4]) // 1000)
            return '{} {} {} / {} / {}'.format(name, url, artist, album, duration)
    elif arg['type'] == 'album':
        ty = '10'
        xpath = '//result/albums/item'
        field = [
            ('./name', '', '{}'),
            ('./id', '', '[\\x0302 https://music.163.com/album?id={} \\x0f]'),
            ('./artists//name', '', 'by {}'),
            ('./company', '', 'via {}'),
            ('./size', '', '{} tracks'),
        ]
        def formatter(e):
            name = e[0]
            url = e[1]
            artist = e[2]
            company = e[3]
            track = e[4]
            return '{} {} {} / {} / {}'.format(name, url, artist, company, track)
    elif arg['type'] == 'artist':
        ty = '100'
        xpath = '//result/artists/item'
        field = [
            ('./name', '', '{}'),
            ('./id', '', '[\\x0302 https://music.163.com/artist?id={} \\x0f]'),
            ('./albumSize', '', '{} albums'),
        ]
        def formatter(e):
            name = e[0]
            url = e[1]
            album = e[2]
            return '{} {} {}'.format(name, url, album)
    elif arg['type'] == 'playlist':
        ty = '1000'
        xpath = '//result/playlists/item'
        field = [
            ('./name', '', '{}'),
            ('./id', '', '[\\x0302 https://music.163.com/playlist?id={} \\x0f]'),
            ('./creator//nickname', '', 'by {}'),
            ('./trackCount', '', '{} tracks'),
        ]
        def formatter(e):
            name = e[0]
            url = e[1]
            creator = e[2]
            track = e[3]
            return '{} {} {} / {}'.format(name, url, creator, track)
    #elif arg['type'] == 'user':
    #    ty = '1002'
    else:
        raise Exception('type check failed')

    arg.update({
        'n': arg['n'] or '1',
        #'url': 'https://music.163.com/api/search/get',
        'url': 'https://music.163.com/weapi/search/get',
        #'url': 'https://music.163.com/weapi/cloudsearch/get/web',
        'xpath': xpath,
    })
    params = {'csrf_token': ''}
    data = {
        'limit': '30',
        'offset': '0',
        's': query,
        'total': 'true',
        'type': ty,
    }
    #data = {
    #    'csrf_token': '',
    #    'hlposttag': '</span>',
    #    'hlpretag': '<span class="s-fc7">',
    #    'limit': '30',
    #    'offset': '0',
    #    's': query,
    #    'total': 'true',
    #    'type': '1',
    #}
    data = music163encrypt(json.dumps(data))
    print(repr(data))
    # from https://github.com/darknessomi/musicbox
    headers = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip,deflate,sdch',
        'Accept-Language': 'zh-CN,zh;q=0.8,gl;q=0.6,zh-TW;q=0.4',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Host': 'music.163.com',
        'Referer': 'https://music.163.com/search/',
        'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.152 Safari/537.36',
    }
    def format(l):
        return map(formatter, l)

    return (yield from jsonxml(arg, [], send, method='POST', headers=headers, data=data, field=field, format=format))
    #return (yield from jsonxml(arg, [], send, method='POST', params=params, headers=headers, data=data, field=field, format=format))


# zhihu header authorization: oauth c3cef7c66a1843f8b3a9e6a1e3160e20


@asyncio.coroutine
def crate(arg, send):
    print('crate')

    arg.update({
        'n': arg['n'] or '3',
        'url': 'https://crates.io/api/v1/crates',
        'xpath': '//crates/item',
    })
    params = {
        'page': 1,
        'per_page': arg['n'],
        'q': arg['query'],
    }
    field = [
        ('./name', '', '{}'),
        ('./max_version', '', '/ {}'),
        ('./id', '', '[\\x0302 https://crates.io/crates/{} \\x0f]'),
        ('./description', '', '{}'),
        #('./repository', '', '{}'),
    ]

    return (yield from jsonxml(arg, [], send, params=params, field=field))


# TODO
@asyncio.coroutine
def leet(arg, send):
    print('leet')

    arg.update({
        'n': '1',
        'url': 'http://www.robertecker.com/hp/research/leet-converter.php',
        'xpath': '//*[@id="comic"]//img',
    })
    field = [
        ('.', 'alt', '{}'),
    ]

    return (yield from html(arg, [], send, field=field))


@asyncio.coroutine
def watson(arg, send):
    pass

help = [
    ('ip'           , 'ip <ip address>'),
    #('whois'        , 'whois <domain>'),
    #('aqi'          , 'aqi <city> [all]'),
    #('bip'          , 'bip <ip address>'),
    #('bweather'     , 'bweather <city>'),
    #('btran'        , 'btran [source lang:target lang] (text)'),
    #('xiaodu'       , 'xiaodu <query>'),
    #('bing'         , 'bing (query) [#max number][+offset]'),
    #('bing'         , 'bing [#max number][+offset] (query)'),
    #('mtran'        , 'mtran [source lang:target lang] (text)'),
    #('couplet'      , 'couplet (shanglian) [#max number][+offset] -- 公门桃李争荣日 法国荷兰比利时'),
    ('google'       , 'google (query) [#max number][+offset]'),
    #('google'       , 'google [#max number][+offset] (query)'),
    ('gtran'        , 'gtran [source lang:target lang] (text)'),
    ('urban'        , 'urban <text> [#max number][+offset]'),
    #('speak'        , 'speak <text>'),
    ('wolfram'      , 'wolfram <query> [#max number][+offset] -- woof~'),
    ('163'          , '163[:type] <query> [#max number][+offset]'),
]

func = [
    #(ip             , r"ip\s+(?P<addr>.+)"),
    #(whois          , r"whois\s+(?P<domain>.+)"),
    #(aqi            , r"aqi\s+(?P<city>.+?)(\s+(?P<all>all))?"),
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
    #(bing           , r"bing(?:\s+(?![#\+])(?P<query>.+?))?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(bing           , r"bing(\s+type:(?P<type>\S+))?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?(\s+(?P<query>.+))?"),
    #(mtran          , r"mtran(\s+(?!:\s)(?P<from>\S+?)?:(?P<to>\S+)?)?(\s+(?P<text>.+))?"),
    #(couplet        , r"couplet(?:\s+(?P<shanglian>\S+))?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(couplet        , r"couplet(?:\s+(?P<shanglian>.+?))?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(mice           , r"mice\s+(?P<input>.+)"),
    #(google         , r"google(\s+type:(?P<type>(web|image)))?\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(google         , r"google\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(google         , r"google(?:\s+(?![#\+])(?P<query>.+?))?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(google         , r"google(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?(\s+(?P<query>.+))?"),
    #(gtran          , r"gtran(\s+(?!:\s)(?P<from>\S+?)?:(?P<to>\S+)?)?(\s+(?P<text>.+))?"),
    (dictg          , r"dict\s+(?P<from>\S+):(?P<to>\S+)\s+(?P<text>.+?)(\s+#(?P<n>\d+))?"),
    (cdict          , r"collins(\s+d:(?P<dict>\S+))?\s+(?P<text>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    # TODO fix api
    #(breezo         , r"breezo\s+(?P<city>.+)"),
    #(speak          , r"speak\s+(?P<text>.+)"),
    #(urban          , r"urban\s+(?P<text>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(urban          , r"rural\s+(?P<text>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(arxiv          , r"arxiv\s+(?P<query>.+?)(\s+xpath:(?P<xpath>.+?))?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(wolfram        , r"wolfram\s+(?P<query>.+?)(\s+xpath:(?P<xpath>.+?))?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(music163       , r"163(?::(?P<type>\S+))?\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(crate          , r"crate\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
]
