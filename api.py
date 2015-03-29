import asyncio
from urllib.parse  import quote_plus, quote
from aiohttp.helpers import BasicAuth
import json
import re
import time

import config
from tool import html, xml, jsonxml, htmlparse

@asyncio.coroutine
def arxiv(arg, send):
    print('arxiv')
    n = int(arg['n'] or 5)
    url = 'http://export.arxiv.org/api/query?search_query={0}&max_results={1}'.format(quote_plus(arg['query']), n)

    arg['n'] = n
    arg['url'] = url
    arg['xpath'] = arg['xpath'] or '//ns:entry/ns:title'

    return (yield from xml(arg, send))

@asyncio.coroutine
def wolfram(arg, send):
    print('wolfram')
    key = config.key['wolfram']
    n = int(arg['n'] or 5)
    url = 'http://api.wolframalpha.com/v2/query?appid={0}&units=metric&input={1}'.format(key, quote_plus(arg['query']))

    arg['n'] = n
    arg['url'] = url
    arg['xpath'] = arg['xpath'] or '//pod'
    field = [('.', 'title', '\\x0304{}:\\x0f'), ('.//plaintext', 'text', '{}')]

    return (yield from xml(arg, send, field=field))

@asyncio.coroutine
def ip(arg, send):
    print('ip')
    url = 'http://ip-api.com/json/' + quote_plus(arg['addr'])

    arg['n'] = 1
    arg['url'] = url
    arg['xpath'] = '/root'
    field = list(map(lambda x: ('./' + x, 'text', '{}'), ['country', 'regionName', 'city', 'isp']))

    return (yield from jsonxml(arg, send, field=field))

@asyncio.coroutine
def whois(arg, send):
    print('whois')
    url = 'http://jsonwhois.com/api/v1/whois?domain=' + quote_plus(arg['domain'])

    key = config.key['jsonwhois']
    headers = {'Accept': 'application/json', 'Authorization': 'Token token=' + key}

    arg['n'] = 1
    arg['url'] = url
    arg['xpath'] = '/root'
    field = list(map(lambda x: ('./' + x, 'text', '{}'), ['status | ./status/item', 'created_on', 'updated_on']))

    return (yield from jsonxml(arg, send, field=field, headers=headers))

@asyncio.coroutine
def aqi(arg, send):
    print('aqi')
    key = config.key['pm25']
    url = 'http://www.pm25.in/api/querys/aqi_details.json?token={0}&avg=true&stations=no&city={1}'.format(key, quote_plus(arg['city']))

    arg['n'] = 3
    arg['url'] = url
    arg['xpath'] = '/root/item'
    field = list(map(lambda x: ('./' + x, 'text', '{}'), ['area', 'quality', 'aqi', 'primary_pollutant', 'time_point']))
    if arg.get('all'):
        l = [('pm2_5', 'PM 2.5'), ('pm10', 'PM 10'), ('co', 'CO'), ('no2', 'NO2'), ('o3', 'O3'), ('o3_8h', 'O3 8h'), ('so2', 'SO2')]
        field += list(map(lambda x: ('./' + x[0], 'text', '\\x0300{0}:\\x0f'.format(x[1]) + ' {}'), l))
        def format(l):
            e = list(l)[0]
            return [' '.join(e[:5]), ', '.join(e[5:])]
    else:
        format = None

    return (yield from jsonxml(arg, send, field=field, format=format))

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
    url = url + 'iplookup?ip=' + quote_plus(arg['addr'])

    arg['n'] = 1
    arg['url'] = url
    arg['xpath'] = '//retData'
    field = list(map(lambda x: ('./' + x, 'text', '{}'), ['country', 'province', 'city', 'district', 'carrier']))

    return (yield from jsonxml(arg, send, field=field))

@asyncio.coroutine
def bid(arg, send):
    print('bid')
    url = 'http://apistore.baidu.com/microservice/'
    url = url + 'icardinfo?id=' + quote_plus(arg['id'])

    arg['n'] = 1
    arg['url'] = url
    arg['xpath'] = '//retData'
    field = list(map(lambda x: ('./' + x, 'text', '{}'), ['sex', 'birthday', 'address']))

    return (yield from jsonxml(arg, send, field=field))

@asyncio.coroutine
def bphone(arg, send):
    print('bphone')
    url = 'http://apistore.baidu.com/microservice/'
    url = url + 'mobilephone?tel=' + quote_plus(arg['tel'])

    arg['n'] = 1
    arg['url'] = url
    arg['xpath'] = '//retData'
    field = list(map(lambda x: ('./' + x, 'text', '{}'), ['telString', 'province', 'carrier']))

    return (yield from jsonxml(arg, send, field=field))

@asyncio.coroutine
def baqi(arg, send):
    print('baqi')
    url = 'http://apistore.baidu.com/microservice/'
    url = url + 'aqi?city=' + quote_plus(arg['city'])

    arg['n'] = 1
    arg['url'] = url
    arg['xpath'] = '//retData'
    field = list(map(lambda x: ('./' + x, 'text', '{}'), ['city', 'level', 'aqi', 'core', 'time']))

    return (yield from jsonxml(arg, send, field=field))

@asyncio.coroutine
def bweather(arg, send):
    print('bweather')
    url = 'http://apistore.baidu.com/microservice/'
    url = url + 'weather?cityname=' + quote_plus(arg['city'])

    arg['n'] = 1
    arg['url'] = url
    arg['xpath'] = '//retData'
    field = list(map(lambda x: ('./' + x, 'text', '{}'), ['city', 'weather', 'temp', 'WS', 'time', 'date']))

    return (yield from jsonxml(arg, send, field=field))

@asyncio.coroutine
def btran(arg, send):
    print('btran')
    # we no longer use baidu translate at apistore.baidu.com
    key = config.key['baidu']
    f = arg['from'] or 'auto'
    t = arg['to'] or 'zh'
    url = 'http://openapi.baidu.com/public/2.0/bmt/translate?client_id={0}&from={1}&to={2}&q={3}'.format(key, quote_plus(f), quote_plus(t), quote_plus(arg['text']))

    arg['n'] = 1
    arg['url'] = url
    arg['xpath'] = '//trans_result/item'
    field = list(map(lambda x: ('./' + x, 'text', '{}'), ['dst']))

    return (yield from jsonxml(arg, send, field=field))

class Get:
    def __init__(self):
        self.l = ''
        self.len = 0
    def __call__(self, l, n=-1, **kw):
        if n < 0:
            self.l += l
        else:
            l = list(l)[0]
            self.l += l[0]
            self.len = int(l[1])

@asyncio.coroutine
def bim(arg, send):
    print('bim')
    n = int(arg['n'] or 1)
    url = 'http://olime.baidu.com/py?inputtype=py&bg=0&ed=20&result=hanzi&resultcoding=unicode&ch_en=0&clientinfo=web&version=1&input='

    l = re.split(r'([^a-z\']+)', arg['pinyin'])
    pinyin = re.compile(r'[a-z\']')
    letter = re.compile(r'[^\']')

    print(l)

    get = Get()
    arg['n'] = 1
    arg['xpath'] = '//result/item[1]/item'
    field = [('./item[1]', 'text', '{}'), ('./item[2]', 'text', '{}')]
    format = lambda x: x
    for e in l:
        try:
            if not pinyin.match(e):
                raise Exception()
            if e[0] == "'":
                get(e[1:])
                continue
            while len(e) > 0:
                print(e)
                arg['url'] = url + quote_plus(e)
                yield from jsonxml(arg, get, field=field, format=format)
                pos = len(e)
                for (i, c) in enumerate(letter.finditer(e)):
                    if i == get.len:
                        pos = c.start()
                        break
                e = e[pos:]
        except:
            get(e)

    line = get.l or 'Σ(っ °Д °;)っ 怎么什么都没有呀'

    return send(line)

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
        yield from jsonxml(self.arg, get, method='POST', data=self.data, headers=self.headers, field=self.field, format=self.format)
        self.time = time.time()
        self.expire = get.expire - 60
        self.key = get.key

@asyncio.coroutine
def bing(arg, send):
    print('bing')
    n = int(arg['n'] or 1)
    #market = 'zh-CN'
    market = 'en-US'
    #url = 'https://api.datamarket.azure.com/Bing/Search/v1/Composite?$format=json&Sources=%27web%2Bimage%2Bvideo%2Bnews%2Bspell%27&Adult=%27Off%27&Market=%27{0}%27&Query=%27{1}%27'.format(quote_plus(market), quote_plus(arg['query']))
    url = 'https://api.datamarket.azure.com/Bing/Search/Composite?$format=json&Sources=%27web%2Bimage%2Bvideo%2Bnews%2Bspell%27&Adult=%27Off%27&Market=%27{0}%27&Query=%27{1}%27'.format(quote_plus(market), quote_plus(arg['query']))

    key = config.key['microsoft']
    auth = BasicAuth(key, key)

    arg['n'] = n
    arg['url'] = url
    arg['xpath'] = '//d/results/item/Web/item'
    field = [('./Title', 'text', '{}'), ('./Url', 'text', '[\\x0302{}\\x0f]'), ('./Description', 'text', '{}')]

    return (yield from jsonxml(arg, send, auth=auth, field=field))

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
#        return (yield from xml(arg, send, headers=headers))
#
#mtran = Mtran()

@asyncio.coroutine
def mtran(arg, send):
    print('mtran')
    f = '&From=%27{0}%27'.format(quote_plus(arg['from'])) if arg['from'] else ''
    t = arg['to'] or 'zh-CHS'
    #url = 'https://api.datamarket.azure.com/Bing/MicrosoftTranslator/v1/Translate?$format=json{0}&To=%27{1}%27&Text=%27{2}%27'.format(quote_plus(f), quote_plus(t), quote_plus(arg['text']))
    url = 'https://api.datamarket.azure.com/Bing/MicrosoftTranslator/Translate?$format=json{0}&To=%27{1}%27&Text=%27{2}%27'.format(f, quote_plus(t), quote_plus(arg['text']))

    key = config.key['microsoft']
    auth = BasicAuth(key, key)

    arg['n'] = 1
    arg['url'] = url
    arg['xpath'] = '//d/results/item'
    field = [('./Text', 'text', '{}')]

    return (yield from jsonxml(arg, send, auth=auth, field=field))

@asyncio.coroutine
def couplet(arg, send):
    print('couplet')
    n = int(arg['n'] or 1)
    url = 'http://couplet.msra.cn/app/CoupletsWS_V2.asmx/GetXiaLian'

    shanglian = arg['shanglian']

    if len(shanglian) > 10:
        send('最多十个汉字喔')
        return

    arg['n'] = n
    arg['url'] = url
    arg['xpath'] = '//d/XialianSystemGeneratedSets/item/XialianCandidates/item'

    data = {
        'shanglian': shanglian,
        'xialianLocker': '0' * len(shanglian),
        'isUpdate': False,
    }
    headers = {'Content-Type': 'application/json'}

    return (yield from jsonxml(arg, send, method='POST', data=json.dumps(data), headers=headers))

@asyncio.coroutine
def mice(arg, send):
    print('mice')
    url = 'http://www.msxiaoice.com/v2/context'

    input = arg['input']

    arg['n'] = 1
    arg['url'] = url
    arg['xpath'] = '//d/XialianSystemGeneratedSets/item/XialianCandidates/item'

    data = {
        'requirement': 1,
        'input': input,
        'args': '',
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    return (yield from jsonxml(arg, send, method='POST', data=data, headers=headers))

@asyncio.coroutine
def dictg(arg, send):
    print('dictg')
    n = int(arg['n'] or 5)
    url = 'https://glosbe.com/gapi/translate?format=json&from={0}&dest={1}&phrase={2}'.format(quote_plus(arg['from']), quote_plus(arg['to']), quote_plus(arg['text']))

    arg['n'] = n
    arg['url'] = url
    arg['xpath'] = '//tuc/item/meanings/item/text'

    return (yield from jsonxml(arg, send))

@asyncio.coroutine
def cdict(arg, send):
    print('cdict')
    n = int(arg['n'] or 5)
    dict = arg['dict'] or 'english'
    url = 'https://api.collinsdictionary.com/api/v1/dictionaries/{0}/search/first/?format=html&q={1}'.format(quote_plus(dict), quote_plus(arg['text']))

    key = config.key['collins']
    headers = {'accessKey': key}

    arg['n'] = n
    arg['url'] = url
    arg['xpath'] = '//entryContent'
    transform = lambda l: htmlparse(l[0].text).xpath('//span[@class = "pos"] | //span[@class = "def"]')

    return (yield from jsonxml(arg, send, transform=transform, headers=headers))

@asyncio.coroutine
def urban(arg, send):
    print('urban')
    n = int(arg['n'] or 1)
    url = 'https://mashape-community-urban-dictionary.p.mashape.com/define?term=' + quote_plus(arg['text'])

    # unofficial
    key = config.key['mashape']
    headers = {'X-Mashape-Key': key}

    arg['n'] = n
    arg['url'] = url
    arg['xpath'] = '//list/item'
    field = [('./definition', 'text', '{}'), ('./permalink', 'text', '[\\x0302{}\\x0f]')]

    return (yield from jsonxml(arg, send, field=field, headers=headers))

@asyncio.coroutine
def breezo(arg, send):
    print('breezo')
    key = config.key['breezo']
    url = 'http://api-beta.breezometer.com/baqi/?key={0}&location={1}'.format(key, quote_plus(arg['city']))

    arg['n'] = 1
    arg['url'] = url
    arg['xpath'] = '/root'
    field = list(map(lambda x: ('./' + x, 'text', '{}'), ['breezometer_description', 'breezometer_aqi', 'dominant_pollutant_text/main', 'random_recommendations/health']))

    return (yield from jsonxml(arg, send, field=field))

@asyncio.coroutine
def btdigg(arg, send):
    print('btdigg')
    n = int(arg['n'] or 1)
    url = 'http://btdigg.org/search?info_hash=&q=' + quote_plus(arg['query'])

    arg['n'] = n
    arg['url'] = url
    arg['xpath'] = '//*[@id="search_res"]/table/tbody/tr'
    field = [('./td/table[1]//a', 'text_content', '\\x0304{}\\x0f'), ('./td/table[2]//td[not(@class)]', 'text_content', '{}'), ('./td/table[2]//td[1]/a', 'href', '[\\x0302{}\\x0f]')]

    return (yield from html(arg, send, field=field))


@asyncio.coroutine
def watson(arg, send):
    pass

help = {
    'ip'             : 'ip <ip address>',
    #'whois'          : 'whois <domain>',
    'aqi'            : 'aqi <city> [all]',
    'bip'            : 'bip <ip address>',
    'bweather'       : 'bweather <city>',
    'btran'          : 'btran [source lang:target lang] <text>',
    'bim'            : 'bim <pinyin> (a valid pinyin starts with a lower case letter, followed by lower case letter or \')',
    'bing'           : 'bing <query> [#max number][+offset]',
    'mtran'          : 'mtran [source lang:target lang] <text>',
    'couplet'        : 'couplet <shanglian (max ten chinese characters)> [#max number][+offset] -- 公门桃李争荣日 法国荷兰比利时',
    'urban'          : 'urban <text> [#max number][+offset]',
    'wolfram'        : 'wolfram <query> [#max number]',
}

func = [
    (ip,              r"ip\s+(?P<addr>.+)"),
    (whois,           r"whois\s+(?P<domain>.+)"),
    (aqi,             r"aqi\s+(?P<city>.+?)(\s+(?P<all>all))?"),
    (bip,             r"bip\s+(?P<addr>.+)"),
    (bid,             r"bid\s+(?P<id>.+)"),
    (bphone,          r"bphone\s+(?P<tel>.+)"),
    (baqi,            r"baqi\s+(?P<city>.+)"),
    (bweather,        r"bweather\s+(?P<city>.+)"),
    (btran,           r"btran(\s+(?!:\s)(?P<from>\S+)?:(?P<to>\S+)?)?\s+(?P<text>.+)"),
    (bim,             r"bim\s+(?P<pinyin>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (bing,            r"bing(\s+type:(?P<type>\S+))?\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (mtran,           r"mtran(\s+(?!:\s)(?P<from>\S+)?:(?P<to>\S+)?)?\s+(?P<text>.+)"),
    (couplet,         r"couplet\s+(?P<shanglian>\S+)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(mice,            r"mice\s+(?P<input>.+)"),
    (dictg,           r"dict\s+(?P<from>\S+):(?P<to>\S+)\s+(?P<text>.+?)(\s+#(?P<n>\d+))?"),
    (cdict,           r"cdict(\s+d:(?P<dict>\S+))?\s+(?P<text>.+?)(\s+#(?P<n>\d+))?"),
    (breezo,          r"breezo\s+(?P<city>.+)"),
    (btdigg,          r"btdigg\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (urban,           r"urban\s+(?P<text>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (arxiv,           r"arxiv\s+(?P<query>.+?)(\s+xpath:(?P<xpath>.+?))?(\s+#(?P<n>\d+))?"),
    (wolfram,         r"wolfram\s+(?P<query>.+?)(\s+xpath:(?P<xpath>.+?))?(\s+#(?P<n>\d+))?"),
]
