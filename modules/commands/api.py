import asyncio
from urllib.parse  import quote_plus, quote
from aiohttp.helpers import BasicAuth
import json
import re
import time

import config
from .tool import xml, jsonxml, htmlparse

@asyncio.coroutine
def arxiv(arg, send):
    print('arxiv')

    arg.update({
        'n': arg['n'] or '5',
        'url': 'http://export.arxiv.org/api/query',
        'xpath': arg['xpath'] or '//ns:entry',
    })
    params = {'search_query': arg['query'], 'max_results': arg['n'], 'sortBy': 'lastUpdatedDate', 'sortOrder': 'descending'}
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
    params = {'appid': config.key['wolfram'], 'units': 'metric', 'format': 'plaintext', 'input': arg['query']}
    field = [('.', 'title', '\\x0300{}:\\x0f'), ('.//plaintext', 'text', '{}')]
    def format(l):
        #r = re.compile(r"(?<!\\)\\:([0-9a-f]{4})")
        r = re.compile(r"\\:([0-9a-f]{4})")
        def f(e):
            if e[1]:
                return ' '.join(r.sub(lambda m: ('\\u' + m.group(1)).encode('utf-8').decode('unicode_escape'), x) for x in e)
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
    headers = {'Accept': 'application/json', 'Authorization': 'Token token=' + config.key['jsonwhois']}
    field = list(map(lambda x: ('./' + x, 'text', '{}'), ['status | ./status/item', 'created_on', 'updated_on']))

    return (yield from jsonxml(arg, [], send, params=params, field=field, headers=headers))

@asyncio.coroutine
def aqi(arg, send):
    print('aqi')

    arg.update({
        'n': '3',
        'url': 'http://www.pm25.in/api/querys/aqi_details.json',
        'xpath': '/root/item',
    })
    params = {'token': config.key['pm25'], 'avg': 'true', 'stations': 'no', 'city': arg['city']}
    field = [('./' + x, 'text', '{}') for x in ['area', 'quality', 'aqi', 'primary_pollutant', 'time_point']]
    if arg.get('all'):
        l = [('pm2_5', 'PM 2.5'), ('pm10', 'PM 10'), ('co', 'CO'), ('no2', 'NO2'), ('o3', 'O3'), ('o3_8h', 'O3 8h'), ('so2', 'SO2')]
        field += [('./' + x[0], 'text', '\\x0300{0}:\\x0f'.format(x[1]) + ' {}') for x in l]
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
    params = {'client_id': config.key['baidu'], 'from': arg['from'] or 'auto', 'to': arg['to'] or 'zh', 'q': ' '.join(lines) or arg['text']}
    field = [('./dst', 'text', '{}')]

    return (yield from jsonxml(arg, [], send, params=params, field=field))

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
        self.sep = re.compile(r"([^a-z']+)")
        self.pinyin = re.compile(r"[a-z']")
        self.letter = re.compile(r"[^']")
        self.comment = re.compile(r"(?:(?<=[^a-z'])|^)''(.*?)''(?:(?=[^a-z'])|$)")
        self.Get = Getter or IM.Getter
    @asyncio.coroutine
    def request(self, e, get):
        pass
    def getpos(self, e, l):
        pass
    @asyncio.coroutine
    def getitem(self, e):
        if not self.pinyin.match(e):
            return e
        if e[0] == "'":
            return e[1:]
        get = self.Get()
        while len(e) > 0:
            #print(e)
            yield from self.request(e, get)
            pos = self.getpos(e, get.len)
            e = e[pos:]
        return get.l
    @asyncio.coroutine
    def __call__(self, pinyin, send):
        print('im')

        l = []
        pos = 0
        for m in self.comment.finditer(pinyin):
            l.extend(self.sep.split(pinyin[pos:m.start()]))
            #l.append("'" + m.group()[2:-2])
            l.append(m.group()[1:-2])
            pos = m.end()
        l.extend(self.sep.split(pinyin[pos:]))
        #l = self.sep.split(pinyin)
        print(l)

        coros = [self.getitem(e) for e in l]
        lines = yield from asyncio.gather(*coros)
        line = ''.join(lines) if lines else 'Σ(っ °Д °;)っ 怎么什么都没有呀'

        return send(line)

class BIM(IM):
    def __init__(self):
        IM.__init__(self)
        self.arg = {'n': '1', 'url': 'http://olime.baidu.com/py', 'xpath': '//result/item[1]/item'}
        self.params = {
            'inputtype': 'py',
            'bg': '0',
            'ed': '1',
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
        self.params['input'] = e
        yield from jsonxml(self.arg, [], get, params=self.params, field=self.field, format=self.format)
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

class GIM(IM):
    def __init__(self):
        IM.__init__(self)
        self.arg = {'n': '1', 'url': 'https://inputtools.google.com/request', 'xpath': '/root/item[2]/item[1]'}
        self.params = {
            'itc': 'zh-t-i0-pinyin',
            'num': '1',
            'cp': '0',
            'cs': '0',
            'ie': 'utf-8',
            'oe': 'utf-8',
            'app': 'demopage',
            'text': '',
        }
        self.field = [('./item[2]/item[1]', 'text', '{}'), ('./item[3]/item[1]', 'text', '{}')]
        self.format = lambda x: x
    @asyncio.coroutine
    def request(self, e, get):
        self.params['text'] = e
        yield from jsonxml(self.arg, [], get, params=self.params, field=self.field, format=self.format)
    def getpos(self, e, l):
        if not (0 < l and l < len(e)):
            return len(e)
        return l
    @asyncio.coroutine
    def __call__(self, arg, send):
        yield from IM.__call__(self, arg['pinyin'], send)

gim = GIM()

# qq

#@asyncio.coroutine
#def qim(arg, send):
#    print('qim')
#    pinyin = arg['pinyin']
#    url = 'http://ime.qq.com/fcgi-bin/getword?q={0}'
#    xpath = '//result/item[1]/item'
#    field = [('./item[1]', 'text', '{}'), ('./item[2]', 'text', '{}')]
#
#    class qimGet:
#        def __init__(self):
#            self.l = ''
#            self.len = 0
#        def __call__(self, l, n=-1, **kw):
#            if n < 0:
#                self.l += l
#            else:
#                l = list(l)[0]
#                self.l += l[0]
#                self.len = int(l[1])
#
#    return (yield from im(pinyin, url, xpath, field, qimGet, send))


# microsoft

class Microsoft:
    class Get:
        def __init__(self):
            self.key = ''
            self.expire = 0
        def __call__(self, l, n=-1, **kw):
            e = list(l)[0]
            self.key = e[0]
            self.expire = int(e[1])
    def __init__(self, client, scope, type):
        self.arg = {
            'url': 'https://datamarket.accesscontrol.windows.net/v2/OAuth2-13',
            'xpath': '/root',
        }
        self.field = [('./access_token', 'text', '{}'), ('./expires_in', 'text', '{}')]
        self.format = lambda x: x
        self.headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        self.data = 'client_id={0}&client_secret={1}&scope={2}&grant_type={3}'.format(quote_plus(client[0]), quote_plus(client[1]), quote_plus(scope), quote_plus(type))
        self.key = ''
        self.time = 0
        self.expire = 0
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
        'Query': "'{0}'".format(' '.join(lines) or arg['query']),
    }
    key = config.key['microsoft']
    auth = BasicAuth(key, key)
    field = [('./Title', 'text', '{}'), ('./Url', 'text', '[\\x0302 {} \\x0f]'), ('./Description', 'text', '{}')]

    return (yield from jsonxml(arg, [], send, params=params, auth=auth, field=field))

#class Mtran(Microsoft):
#    def __init__(self):
#        super().__init__(config.key['microsoft'], 'http://api.microsofttranslator.com', 'client_credentials')
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
        'Text': "'{0}'".format(' '.join(lines) or arg['text']),
    }
    if arg['from']:
        params['From'] = "'{0}'".format(arg['from'])
    key = config.key['microsoft']
    auth = BasicAuth(key, key)
    field = [('./Text', 'text', '{}')]

    return (yield from jsonxml(arg, [], send, params=params, auth=auth, field=field))

@asyncio.coroutine
def couplet(arg, send):
    print('couplet')

    shanglian = arg['shanglian']
    if len(shanglian) > 10:
        send('最多十个汉字喔')
        return

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
    url = 'http://www.msxiaoice.com/v2/context'

    input = arg['input']

    arg['n'] = '1'
    arg['url'] = url
    arg['xpath'] = '//d/XialianSystemGeneratedSets/item/XialianCandidates/item'

    data = {
        'requirement': 1,
        'input': input,
        'args': '',
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

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
    params = {'key': config.key['google'], 'cx': config.key['googleseid'], 'q': ' '.join(lines) or arg['query']}
    field = [('./title', 'text', '{}'), ('./link', 'text', '[\\x0302 {} \\x0f]'), ('./snippet', 'text', '{}')]

    return (yield from jsonxml(arg, [], lambda m, **kw: send(m, newline=False, **kw), params=params, field=field))


@asyncio.coroutine
def dictg(arg, send):
    print('dictg')

    arg.update({
        'url': 'https://glosbe.com/gapi/translate',
        'xpath': '//tuc/item/meanings/item/text',
    })
    params = {'format': 'json', 'from': arg['from'], 'dest': arg['to'], 'phrase': arg['text']}

    return (yield from jsonxml(arg, [], send, params=params))

@asyncio.coroutine
def cdict(arg, send):
    print('cdict')

    arg.update({
        'url': 'https://api.collinsdictionary.com/api/v1/dictionaries/{0}/search/first/'.format(arg['dict'] or 'english'),
        'xpath': '//entryContent',
    })
    params = {'format': 'html', 'q': arg['text']}
    headers = {'accessKey': config.key['collins']}
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
    headers = {'X-Mashape-Key': config.key['mashape']}
    field = [('./definition', 'text', '{}'), ('./permalink', 'text', '[\\x0302 {} \\x0f]')]

    return (yield from jsonxml(arg, [], send, params=params, field=field, headers=headers))

@asyncio.coroutine
def breezo(arg, send):
    print('breezo')

    arg.update({
        'n': '1',
        'url': 'http://api-beta.breezometer.com/baqi/',
        'xpath': '/root',
    })
    params = {'key': config.key['breezo'], 'location': arg['city']}
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
    params = {'user_key': config.key['howtospeak'], 'notrans': '0', 'text': arg['text']}

    return (yield from jsonxml(arg, [], send, params=params))

@asyncio.coroutine
def watson(arg, send):
    pass

help = [
    ('ip'           , 'ip <ip address>'),
    #('whois'        , 'whois <domain>'),
    ('aqi'          , 'aqi <city> [all]'),
    ('bip'          , 'bip <ip address>'),
    ('bweather'     , 'bweather <city>'),
    ('btran'        , 'btran [source lang:target lang] (text)'),
    ('bim'          , 'bim <pinyin> (a valid pinyin starts with a lower case letter, followed by lower case letters or \'; use \'\' in pair for comment)'),
    ('gim'          , 'gim <pinyin> (a valid pinyin starts with a lower case letter, followed by lower case letters or \'; use \'\' in pair for comment)'),
    #('bing'         , 'bing <query> [#max number][+offset]'),
    ('bing'         , 'bing [#max number][+offset] (query)'),
    ('mtran'        , 'mtran [source lang:target lang] (text)'),
    ('couplet'      , 'couplet <shanglian (max ten chinese characters)> [#max number][+offset] -- 公门桃李争荣日 法国荷兰比利时'),
    #('google'       , 'google <query> [#max number][+offset]'),
    ('google'       , 'google [#max number][+offset] (query)'),
    ('urban'        , 'urban <text> [#max number][+offset]'),
    ('speak'        , 'speak <text>'),
    ('wolfram'      , 'wolfram <query> [#max number][+offset]'),
]

func = [
    (ip             , r"ip\s+(?P<addr>.+)"),
    (whois          , r"whois\s+(?P<domain>.+)"),
    (aqi            , r"aqi\s+(?P<city>.+?)(\s+(?P<all>all))?"),
    (bip            , r"bip\s+(?P<addr>.+)"),
    (bid            , r"bid\s+(?P<id>.+)"),
    (bphone         , r"bphone\s+(?P<tel>.+)"),
    (baqi           , r"baqi\s+(?P<city>.+)"),
    (bweather       , r"bweather\s+(?P<city>.+)"),
    #(btran          , r"btran(\s+(?!:\s)(?P<from>\S+)?:(?P<to>\S+)?)?\s+(?P<text>.+)"),
    (btran          , r"btran(\s+(?!:\s)(?P<from>\S+)?:(?P<to>\S+)?)?(\s+(?P<text>.+))?"),
    #(bim            , r"bim\s+(?P<pinyin>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (bim            , r"bim\s+(?P<pinyin>.+)"),
    (gim            , r"gim\s+(?P<pinyin>.+)"),
    #(qim            , r"qim\s+(?P<pinyin>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(bing           , r"bing(\s+type:(?P<type>\S+))?\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (bing           , r"bing(\s+type:(?P<type>\S+))?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?(\s+(?P<query>.+))?"),
    #(mtran          , r"mtran(\s+(?!:\s)(?P<from>\S+)?:(?P<to>\S+)?)?\s+(?P<text>.+)"),
    (mtran          , r"mtran(\s+(?!:\s)(?P<from>\S+)?:(?P<to>\S+)?)?(\s+(?P<text>.+))?"),
    (couplet        , r"couplet\s+(?P<shanglian>\S+)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(mice           , r"mice\s+(?P<input>.+)"),
    #(google         , r"google(\s+type:(?P<type>(web|image)))?\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(google         , r"google\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (google         , r"google(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?(\s+(?P<query>.+))?"),
    (dictg          , r"dict\s+(?P<from>\S+):(?P<to>\S+)\s+(?P<text>.+?)(\s+#(?P<n>\d+))?"),
    (cdict          , r"cdict(\s+d:(?P<dict>\S+))?\s+(?P<text>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (breezo         , r"breezo\s+(?P<city>.+)"),
    (speak          , r"speak\s+(?P<text>.+)"),
    (urban          , r"urban\s+(?P<text>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(arxiv          , r"arxiv\s+(?P<query>.+?)(\s+xpath:(?P<xpath>.+?))?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (wolfram        , r"wolfram\s+(?P<query>.+?)(\s+xpath:(?P<xpath>.+?))?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
]
