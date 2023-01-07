from urllib.parse  import parse_qs, quote_plus, urlparse
import re

from .common import Get
from .tool import html, xml, addstyle, htmlparse
#from .tool import fetch, htmltostr, html, xml, addstyle, jsonparse, htmlparse
from .api import google

# github search?
# oeis.org
# reddit comment like zhihu

# html parse


async def arxiv(arg, send):
    print('arxiv')

    arg.update({
        'n': arg['n'] or '3',
        'url': 'https://arxiv.org/search',
        #'xpath': '//*[@id="dlpage"]/dl/dt',
        'xpath': '//*[@class="arxiv-result"]',
    })
    params = {'query': arg['query'], 'searchtype': 'all'}
    def format(self, es):
        field = [
            #('./span/a[1]', 'text', lambda x: self.iter_first(x)[6:]),
            #('./following-sibling::dd[1]/div/div[1]/span', 'tail', self.iter_first),
            ('./div/p/a', 'text', lambda x: self.iter_first(x)[6:]),
            ('./p[1]', '', lambda x: self.iter_first(x).strip()),
        ]
        return (['[\\x0302{0}\\x0f] {1}'.format(*self.get_fields(self.get, e, field))] for e in es)

    return (await html(arg, [], send, params=params, format_new=format))


async def vixra(arg, send):
    print('vixra')

    arg.update({
        'query': 'site:vixra.org/abs {}'.format(arg['query'])
    })

    return (await google(arg, [], send))


async def zhihu(arg, send):
    print('zhihu')

    def image(e):
        for ns in e.xpath('.//noscript'):
            ns.text = ''
        for img in e.xpath('.//img'):
            src = img.attrib.get('data-actualsrc')
            if src:
                if src[:2] == '//':
                    img.tail = ' [\\x0302 http:{0} \\x0f] '.format(src) + (img.tail or '')
                else:
                    img.tail = ' [\\x0302 {0} \\x0f] '.format(src) + (img.tail or '')
        return e

    arg.update({
        'n': '1',
        'xpath': '//*[@id="root"]//div[@class="QuestionAnswer-content"]//span[contains(@class, "RichText")]',
    })
    preget = lambda e: image(e)

    return (await html(arg, [], send, preget=preget))


async def bihu(arg, send):
    print('bihu')

    def image(e):
        for ns in e.xpath('.//noscript'):
            ns.text = ''
        for img in e.xpath('.//img'):
            img.tail = ' <img> ' + (img.tail or '')
        return e
    def bio(e):
        for t in e.xpath('.//*[@class="zu-question-my-bio"]'):
            t.text = ''
        for t in e.xpath('.//*[@class="zm-item-link-avatar"]/*'):
            t.getparent().remove(t)
        for t in e.xpath('.//*[@class="UserLink-badge"]/*'):
            t.getparent().remove(t)
        return e

    arg.update({
        #'xpath': '//*[@id="zh-question-answer-wrap"]/div',
        #'xpath': '//*[@id="root"]//div[@class="ContentItem"]',
        'xpath': '//*[@id="root"]//div[@class="ContentItem AnswerItem"]',
    })
    field = [
        ##('./div[1]/button[1]/span[2]', 'text', '{}'),
        #('./div[1]/button[1]/span[1]', 'text', '{}'),
        ##('./div[2]/div[1]/h3', '', '{}'),
        ##('./div[2]/div[1]/*[contains(@class, "author-link") or contains(@class, "name")]', '', '{}'),
        #('.//span[contains(@class, "author-link-line")]/*[contains(@class, "author-link") or contains(@class, "name")]', '', '{}'),
        ##('./div[3]/div', '', '{}'),
        #('./div[3]/div[contains(@class, "zm-editable-content")]', '', '{}'),
        #('./div[4]/div/span[1]/a', 'href', '{}'),
        #('./a[1]', 'name', '{}'),
        ('.//button[contains(@class, "VoteButton--up")]', '', '{}'),
        ('.//div[contains(@class, "AuthorInfo-content")]//span[contains(@class, "UserLink")]', '', '{}'),
        ('.//span[contains(@class, "RichText")]', '', '{}'),
        ('.//div[contains(@class, "ContentItem-time")]/a', 'href', '{}'),
    ]
    preget = lambda e: image(bio(e))
    def format(l):
        for e in l:
           vote = e[0]
           name = e[1].strip().strip('，')
           digest = e[2].strip()
           length = 120
           if len(digest) > length:
               digest = digest[:length] + '\\x0f...'
           #digest = digest[:length] + '\\x0f...'
           digest = digest.replace('\n', ' ')
           #link = '/' + e[3].split('/', 3)[-1]
           #anchor = '#' + e[4]
           #anchor = '#'
           #yield '[\\x0304{0}\\x0f] \\x0300{1}:\\x0f {2} \\x0302{3}\\x0f \\x0302{4}\\x0f'.format(vote, name, digest, link, anchor)
           #yield '[\\x0304{0}\\x0f] \\x16{1}:\\x0f {2} \\x0302{3}\\x0f \\x0302{4}\\x0f'.format(vote, name, digest, link, anchor)
           #yield '[\\x0304{0}\\x0f] \\x16{1}:\\x0f {2} \\x0302{3}\\x0f'.format(vote, name, digest, link)
           yield '[\\x0304{0}\\x0f] \\x02{1}:\\x0f {2}'.format(vote, name, digest)

    return (await html(arg, [], send, field=field, preget=preget, format=format))


async def pm25(arg, send):
    print('pm25')

    city = {
        '北京': '1',
        '成都': '2',
        '广州': '3',
        '上海': '4',
        '沈阳': '5',
    }

    try:
        location = city[arg['city']]
    except:
        send('只有如下城市: ' + ', '.join(city.keys()))
        return

    arg.update({
        'n': '1',
        'url': 'http://www.stateair.net/web/post/1/{0}.html'.format(location),
        'xpath': '//*[@id="content"]/div[2]/div[1]/div/div[3]/table/tbody',
    })
    field = [('./' + x, '', '{}') for x in ['tr[3]/td', 'tr[2]/td', 'tr[5]//span', 'tr[1]//span']]
    def format(l):
        e = list(l)[0]
        return [', '.join(e).replace('\n', '')]

    return (await html(arg, [], send, field=field, format=format))


async def btdigg(arg, send):
    print('btdigg')

    arg.update({
        'n': str(int(arg['n'] or '1') * 2),
        'url': 'http://btdigg.org/search',
        'xpath': '//*[@id="search_res"]/table/tbody/tr',
    })
    params = {'info_hash': '', 'q': arg['query']}
    #field = [('./td/table[1]//a', 'text_content', '\\x0304{}\\x0f'), ('./td/table[2]//td[not(@class)]', 'text_content', '{}'), ('./td/table[2]//td[1]/a', 'href', '[\\x0302 {} \\x0f]')]
    # magnet link
    field = [
        ('./td/table[1]//a', '', '\\x0300{}\\x0f'),
        ('./td/table[2]//td[not(@class)]', '', '{}'),
        ('./td/table[2]//td[1]/a', 'href', '\\x0302{}\\x0f'),
    ]

    def format(l):
        line = []
        for e in l:
            line.append(' '.join(e[:2]))
            line.append(e[2])
        return line

    return (await html(arg, [], send, params=params, field=field, format=format))


async def man(arg, send):
    print('man')

    section = arg['section'].lower() if arg['section'] else arg['section']
    name = arg['name'].lower()

    url = 'http://linux.die.net/man/'
    if not section:
        a = {
            'n': '1',
            'url': url + '{0}.html'.format(name[0] if 'a' <= name[0] and name[0] <= 'z' else 'other'),
            'xpath': '//*[@id="content"]/dl/dt/a[starts-with(text(), "{0}")]'.format(name),
        }
        f = [('.', 'href', '{}')]
        get = Get()
        await html(a, [], get, field=f)
        path = get.line[0]
    else:
        path = '{0}/{1}'.format(section, name)

    arg.update({
        'n': '1',
        'url': url + path,
        'xpath': '//head',
    })
    field = [
        ('./title', '', '{}'),
        ('./base', 'href', '[\\x0302 {} \\x0f]'),
        ('./meta[@name = "description"]', 'content', '{}'),
    ]

    return (await html(arg, [], send, field=field))


async def manfreebsd(arg, send):
    print('manfreebsd')

    arg.update({
        'n': '1',
        'url': 'https://www.freebsd.org/cgi/man.cgi',
        'xpath': '//*[@id="content"]',
    })
    params = {
        'query': arg['query'].lower(),
        'apropos': 0,
        'sektion': 0,
        'manpath': 'FreeBSD 13.0-RELEASE and Ports',
        'arch': 'default',
        'format': 'html',
    }
    field = [
        ('./pre/*[@name="NAME"]/following-sibling::b[1]', '', '{}'),
        ('./pre/*[@name="NAME"]/following-sibling::b[1]', 'tail', '{}'),
        ('./p/a', 'href', '[\\x0302 {} \\x0f]'),
    ]
    def format(l):
        return map(lambda e: '{0} {1} {2}'.format(e[0], e[1].strip(), e[2]), l)

    return (await html(arg, [], send, params=params, field=field, format=format))


async def gauss(arg, send):
    print('gauss')

    arg.update({
        'n': arg['n'] or '1',
        'url': 'http://www.gaussfacts.com/random',
        'xpath': '//*[@id="wrapper"]/div/p/a[@class="oldlink"]',
    })

    return (await html(arg, [], send))


async def foldoc(arg, send):
    print('foldoc')

    def clean(e):
        for s in e.xpath('.//script | .//style'):
            #s.getparent().remove(s)
            # don't remove tail
            s.text = ''
        for span in e.xpath('.//span[@class="mw-editsection"]'):
            span.getparent().remove(span)
        return e

    arg.update({
        'n': arg['n'] or '1',
        'url': 'http://foldoc.org/' + quote_plus(arg['query']),
        'xpath': '//*[@id="content"]/p',
    })

    get = lambda e, f: addstyle(clean(e)).xpath('string()')

    return (await html(arg, [], send, get=get))


async def wiki(arg, send):
    print('wiki')

    if arg['site'] == 'cpp':
        arg.update({
            'n': arg['n'] or '1',
            'url': 'https://en.cppreference.com/mwiki/api.php',
            'xpath': '//page/@title',
        })
        params = {
            'format': 'xml',
            'action': 'query',
            'generator': 'search',
            'gsrlimit': '1',
            'gsrwhat': 'text',
            'gsrsearch': arg['query'],
            'prop': 'revisions',
            'rvprop': 'content',
            'rvparse': '',
        }
        def format(l):
            return map(lambda e: '[\\x0302 http://en.cppreference.com/w/{0} \\x0f]'.format(e[0].replace(' ', '_')), l)
        return (await xml(arg, [], send, params=params, format=format))

    def clean(e):
        for s in e.xpath('.//script | .//style'):
            #s.getparent().remove(s)
            # don't remove tail
            s.text = ''
        for span in e.xpath('.//span[@class="mw-editsection"]'):
            span.getparent().remove(span)
        return e

    site = {
        # linux
        #'arch': 'https://wiki.archlinux.org/',
        #'gentoo': 'https://wiki.gentoo.org/',
        # wikipedia
        'zh': 'https://zh.wikipedia.org/w/',
        'classical': 'https://zh-classical.wikipedia.org/w/',
        'en': 'https://en.wikipedia.org/w/',
        'ja': 'https://ja.wikipedia.org/w/',
        # misc
        'poke': 'https://wiki.52poke.com/',
        #'pokemon': 'http://www.pokemon.name/w/',
    }

    try:
        url = site[arg['site'] or 'zh']
    except:
        raise Exception("Do you REALLY need this wiki?")

    arg.update({
        'n': arg['n'] or '1',
        'url': url + 'api.php',
        'xpath': '//page',
    })
    params = {
        'format': 'xml',
        'action': 'query',
        'generator': 'search',
        'gsrlimit': '1',
        'gsrwhat': 'nearmatch',
        'gsrsearch': arg['query'],
        'prop': 'revisions',
        'rvprop': 'content',
        'rvparse': '',
    }
    # don't select following nodes
    # script                 -> js
    # div and table          -> box, table and navbox
    # h2                     -> section title
    # preceding-sibling      -> nodes after navbox or MOEAttribute, usually external links
    xpath = ('/*['
        # filter script, style and section title
        #'not(self::script or self::style or self::h2)'
        #'not(self::div or self::table)'
        # or just select p and ul ?
        '(self::p or self::ul)'
        ' and '
        # select main part
        'not('
        'following-sibling::div[@class="infotemplatebox"]'
        ' or '
        'preceding-sibling::div[@class="MOEAttribute"]'
        ' or '
        'preceding-sibling::table[@class="navbox"]'
        ')'
        ']')
    def transform(l):
        if l:
            #pageid = l[0].get('pageid')
            return htmlparse(l[0].xpath('//rev')[0].text).xpath('//*[@class="mw-parser-output"]' + xpath)
        else:
            raise Exception("oops...")

    get = lambda e, f: addstyle(clean(e)).xpath('string()')

    #return (await xml(arg, [], send, params=params, transform=transform, get=get))
    try:
        await xml(arg, [], send, params=params, transform=transform, get=get)
    except:
        params['gsrwhat'] = 'text'
        await xml(arg, [], send, params=params, transform=transform, get=get)


async def xkcd(arg, send):
    print('xkcd')

    # latest by default
    if arg['number'] == None:
        url = 'https://xkcd.com/'
    elif arg['number'] == 'random':
        url = 'https://c.xkcd.com/random/comic/'
    else:
        url = 'https://xkcd.com/{0}/'.format(arg['number'])

    arg.update({
        'n': '1',
        'url': url,
        'xpath': '//*[@id="middleContainer"]',
    })
    field = [
        #('./br[1]', 'tail', '{}'),
        ('./a[1]', 'href', '{}'),
        ('.//*[@id="comic"]//img', 'alt', '{}'),
        ('.//*[@id="comic"]//img', 'src', '[\\x0302 http:{} \\x0f]'),
        ('.//*[@id="comic"]//img', 'title', '{}'),
    ]
    def format(l):
        return map(lambda e: '[\\x0304{0}\\x0f] {1} {2} {3}'.format(re.search(r"[0-9]+", e[0]).group(), e[1], e[2], e[3]), l)

    return (await html(arg, [], send, field=field, format=format))


async def etymology(arg, send):
    print('etymology')

    def foreign(e):
        for span in e.xpath('.//span[@class="foreign"]'):
            span.text = '\\x02' + (span.text or '')
            span.tail = '\\x0f' + (span.tail or '')
        return e

    arg.update({
        'n': arg['n'] or '1',
        'url': 'http://www.etymonline.com/search',
        'xpath': '//a[contains(@class, "word")]',
    })
    params = {
        'q': arg['query'],
    }
    field = [
        ('.//h1', '', '\\x02{}\\x0f'),
        ('.//object', '', '{}'),
    ]
    get = lambda e, f: addstyle(foreign(e)).xpath('string()')

    return (await html(arg, [], send, params=params, field=field, get=get))


async def lmgtfy(arg, send):
    print('lmgtfy')

    return send('[\\x0302 https://lmgtfy.com/?q={} \\x0f]'.format(quote_plus(arg['query'])))


async def commit(arg, send):
    print('commit')

    arg.update({
        'n': '1',
        'url': 'http://whatthecommit.com/index.txt',
        'xpath': '.',
    })

    return (await html(arg, [], send))


async def ipip(arg, send):
    print('ipip')

    arg.update({
        'n': '1',
        'url': 'http://www.ipip.net/ip.html',
        'xpath': '//*[@id="myself"]',
    })
    field = [
        ('.', '', '{}'),
    ]
    data = {
        'ip': arg['addr'],
    }

    #return (await html(arg, [], send, method='POST', data=data, field=field))
    return (await html(arg, [], send, method='POST', data=data))


# TODO pronunciation
async def kotobank(arg, send):
    print('kotobank')

    def clean(e):
        for span in e.xpath('.//span[@class="hinshi"]'):
            span.text = ''
        return e

    arg.update({
        'n': '1',
        'url': 'https://kotobank.jp/word/{0}'.format(arg['query']),
        'xpath': '//article[contains(@class, "daijisen")]//section[@class="description"]',
    })
    preget = lambda e: clean(e)

    return (await html(arg, [], send, preget=preget))


async def plato(arg, send):
    print('plato')

    arg.update({
        'n': arg['n'] or '1',
        'url': 'https://plato.stanford.edu/search/searcher.py',
        'xpath': '//div[contains(@class, "result_listing")]',
    })
    params = {'query': arg['query']}
    field = [
        ('./div[contains(@class, "result_title")]/a', '', '{}'),
        ('./div[contains(@class, "result_url")]/a', '', '[\\x0302 {} \\x0f]'),
        ('./div[contains(@class, "result_snippet")]', '', '{}'),
    ]
    def format(l):
        return map(lambda e: '{0} {1} {2}'.format(e[0].strip(), e[1], e[2].strip().replace('\n', ' ')), l)

    return (await html(arg, [], send, params=params, field=field, format=format))


# TODO ugly
async def bangumi(arg, send):
    print('bangumi')

    arg.update({
        'n': arg['n'] or '1',
        'url': 'https://bangumi.tv/subject_search/{}'.format(arg['query']),
        'xpath': '//ul[contains(@class, "browserFull")]/li/div',
    })
    field = [
        ('.//a[contains(@class, "l")]', '', '{}'),
        ('.//small', '', '({})'),
        ('.//a[contains(@class, "l")]', 'href', '[\\x0302 https://bangumi.tv{} \\x0f]'),
        ('.//p[contains(@class, "info")]', '', '{}'),
    ]
    def format(l):
        return map(lambda e: '{0} {1} {2} {3}'.format(e[0], e[1], e[2], e[3].strip().replace('\n', ' ')), l)

    return (await html(arg, [], send, field=field, format=format))


# TODO ugly
async def douban(arg, send):
    print('douban')

    arg.update({
        'n': arg['n'] or '1',
        'url': 'https://www.douban.com/search',
        'xpath': '//div[contains(@class, "result")]//div[contains(@class, "title")]',
    })
    params = {'q': arg['query']}
    field = [
        ('./h3/span[1]', '', '{}'),
        ('./h3/a', '', '{}'),
        ('./h3/a', 'href', '{}'),
        ('./div[contains(@class, "rating-info")]', '', '{}'),
    ]
    def format(l):
        return map(lambda e: '{0} {1} [\\x0302 {2} \\x0f] {3}'.format(e[0], e[1], parse_qs(urlparse(e[2]).query)['url'][0], e[3].strip().replace('\n', ' ')), l)

    return (await html(arg, [], send, params=params, field=field, format=format))


async def killteleboto(arg, send):
    print('killteleboto')

    return send('Avada Kedavra!\\x030', raw=True)


func = [
    (zhihu          , r"zhihu\s+(?P<url>http\S+)"),
    #(bihu           , r"bihu\s+(?P<url>http\S+)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (bihu           , r"bihu\s+(?P<url>http\S+)"),
    (pm25           , r"pm2.5\s+(?P<city>.+)"),
    #(btdigg         , r"btdigg\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (man            , r"man(\s+(?P<section>[1-8ln]))?\s+(?P<name>.+)"),
    (manfreebsd     , r"man:freebsd\s+(?P<query>.+)"),
    (man            , r"woman(\s+(?P<section>[1-8ln]))?\s+(?P<name>.+)"),
    (manfreebsd     , r"woman:freebsd\s+(?P<query>.+)"),
    (gauss          , r"gauss(\s+#(?P<n>\d+))?"),
    (foldoc         , r"foldoc\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (arxiv          , r"arxiv\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (vixra          , r"vixra\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (wiki           , r"wiki(?::(?P<site>\S+))?\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (xkcd           , r"xkcd(\s+(?P<number>(\d+)|(random)))?"),
    (etymology      , r"etymology\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (lmgtfy         , r"lmgtfy\s+(?P<query>.+?)"),
    (commit         , r"commit"),
    (ipip           , r"ipip\s+(?P<addr>.+)"),
    (kotobank       , r"kotobank\s+(?P<query>.+)"),
    (plato          , r"plato\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    #(bangumi        , r"bangumi\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (douban         , r"douban\s+(?P<query>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (killteleboto   , r"killteleboto"),
]
