import asyncio
import re
import json
from urllib.parse  import quote_plus, quote, urldefrag
from aiohttp       import request
from lxml          import etree
import lxml.html
import html5lib
from dicttoxml import dicttoxml

@asyncio.coroutine
def fetch(method, url, n, func, send, **kw):
    print('fetch')
    #r = yield from asyncio.wait_for(request('GET', urldefrag(url)[0], **kw), 1)
    r = yield from request(method, urldefrag(url)[0], **kw)
    #byte = yield from r.read()
    try:
        byte = yield from r.text()
    except:
        print('bad encoding')
        byte = yield from r.read()
    print('get byte')
    l = yield from func(byte)
    send(l, n=n, llimit=10)

def addstyle(e):
    # br to newline
    #print(etree.tostring(e))
    for br in e.xpath('.//br'):
        br.tail = '\n' + br.tail if br.tail else '\n'
    for b in e.xpath('.//b'):
        b.text = '\\x02' + b.text if b.text else '\\x02'
        b.tail = '\\x02' + b.tail if b.tail else '\\x02'
    for i in e.xpath('.//i'):
        i.text = '\\x1d' + i.text if i.text else '\\x1d'
        i.tail = '\\x1d' + i.tail if i.tail else '\\x1d'
    for u in e.xpath('.//u'):
        u.text = '\\x1f' + u.text if u.text else '\\x1f'
        u.tail = '\\x1f' + u.tail if u.tail else '\\x1f'
    return e

# use html5lib for standard compliance
def htmlparse(t):
    return html5lib.parse(t, treebuilder='lxml', namespaceHTMLElements=False)
def htmlparsefast(t, *, parser=None):
    return lxml.html.fromstring(t, parser=parser)

def htmltostr(t):
    return addstyle(htmlparse(t)).xpath('string()')

def xmlparse(t):
    try:
        return etree.XML(t)
    except:
        return etree.XML(t.encode('utf-8'))

def jsonparse(t):
    try:
        return json.loads(t)
    except:
        return json.loads(t.decode('utf-8'))

def parsefield(field):
    if field:
        # no # in xpath
        f = re.finditer(r"\s*(?P<xpath>[^#]+)?#(?P<field>[^\s']+)?(?:'(?P<format>[^']+)')?", field)
        def getitem(e):
            d = e.groupdict()
            return (d['xpath'] or '.', d['field'] or 'text_content', d['format'] if d['format'] else '{}')
        return list(map(getitem, f))
    else:
        return [('.', 'text_content', '{}')]

def getfield(field, get):
    def getl(e, f):
        def gete(e):
            item = get(e, f[1])
            return str(item).strip() if item else ''
        l = list(filter(lambda x: any(x), map(gete, e.xpath(f[0]))))
        return f[2].format(', '.join(l)) if l else ''

    def getf(e):
        return list(map(lambda f: getl(e, f), field))

    return getf

@asyncio.coroutine
def html(arg, send, *, method='GET', field=None, get=None, transform=None, format=None, **kw):
    print('html')

    #n = int(arg['n']) if arg['n'] else 5
    n = int(arg.get('n') or 5)
    offset = int(arg.get('offset') or 0)
    url = arg['url']
    xpath = arg['xpath']
    #field = field or parsefield(arg['field'])
    field = field or parsefield(arg.get('field'))

    print(field)
    ns = {'re': 'http://exslt.org/regular-expressions'}
    transform = transform or (lambda l: l)
    get = get or (lambda e, f: addstyle(e).xpath('string()') if f == 'text_content' else getattr(e, f) if hasattr(e, f) else e.attrib.get(f))
    getf = getfield(field, get)
    #formatl = (lambda l: strtoesc(arg['format']).format(*l)) if arg['format'] else (lambda l: ' '.join(l))
    format = format or ((lambda l: map(lambda e: arg['format'].format(*e), l)) if arg.get('format') else (lambda l: map(lambda e: ' '.join(e), l)))

    @asyncio.coroutine
    def func(byte):
        l = htmlparse(byte).xpath(xpath, namespaces=ns)
        l = transform(l)[offset:]
        l = filter(lambda e: any(e), map(getf, l))
        #return map(lambda e: formatl(e), l)
        return format(l)

    return (yield from fetch(method, url, n, func, send, **kw))

@asyncio.coroutine
def xml(arg, send, *, method='GET', field=None, get=None, transform=None, format=None, **kw):
    print('xml')

    n = int(arg.get('n') or 5)
    offset = int(arg.get('offset') or 0)
    url = arg['url']
    xpath = arg['xpath']
    field = field or parsefield(arg.get('field'))

    print(field)
    ns = {'re': 'http://exslt.org/regular-expressions'}
    transform = transform or (lambda l: l)
    get = get or (lambda e, f: htmltostr(e.text) if f == 'text_content' else getattr(e, f) if hasattr(e, f) else e.attrib.get(f))
    getf = getfield(field, get)
    format = format or ((lambda l: map(lambda e: arg['format'].format(*e), l)) if arg.get('format') else (lambda l: map(lambda e: ' '.join(e), l)))

    @asyncio.coroutine
    def func(byte):
        t = xmlparse(byte)
        ns.update(t.nsmap)
        xmlns = ns.pop(None, None)
        if xmlns:
            ns['ns'] = xmlns
        l = t.xpath(xpath, namespaces=ns)
        l = transform(l)[offset:]
        l = filter(lambda e: any(e), map(getf, l))
        return format(l)

    return (yield from fetch(method, url, n, func, send, **kw))

@asyncio.coroutine
def jsonxml(arg, send, *, method='GET', field=None, get=None, transform=None, format=None, **kw):
    print('jsonxml')

    n = int(arg.get('n') or 5)
    offset = int(arg.get('offset') or 0)
    url = arg['url']
    xpath = arg['xpath']
    field = field or parsefield(arg.get('field'))

    print(field)
    ns = {'re': 'http://exslt.org/regular-expressions'}
    transform = transform or (lambda l: l)
    get = get or (lambda e, f: e.text)
    getf = getfield(field, get)
    format = format or ((lambda l: map(lambda e: arg['format'].format(*e), l)) if arg.get('format') else (lambda l: map(lambda e: ' '.join(e), l)))

    @asyncio.coroutine
    def func(byte):
        j = jsonparse(byte)
        #print(j)
        #print(dicttoxml(j))
        l = xmlparse(dicttoxml(j)).xpath(xpath, namespaces=ns)
        l = transform(l)[offset:]
        l = filter(lambda e: any(e), map(getf, l))
        return format(l)

    return (yield from fetch(method, url, n, func, send, **kw))

@asyncio.coroutine
def regex(arg, send, **kw):
    print('regex')

    n = int(arg.get('n') or 5)
    url = arg['url']

    reg = re.compile(arg['regex'])

    @asyncio.coroutine
    def func(byte):
        l = reg.finditer(byte.decode('utf-8'))
        return map(lambda e: ', '.join(e.groups()), l)

    return (yield from fetch('GET', url, n, func, send, **kw))


help = {
    'html'           : 'html <url> <xpath (no { allowed)> [output fields (e.g. {[xpath (no { allowed)]#[attrib][\'format\']})] [#max number][+offset]',
    'xml'            : 'xml <url> <xpath (no { allowed)> [output fields (e.g. {[xpath (no { allowed)]#[attrib][\'format\']})] [#max number][+offset]',
    'json'           : 'json <url> <xpath (no { allowed)> [output fields (e.g. {[xpath (no { allowed)]#[attrib][\'format\']})] [#max number][+offset]',
    'regex'          : 'regex <url> <regex> [max number]',
}

func = [
    # no { in xpath
    (html,            r"html\s+(?P<url>\S+)\s+(?P<xpath>[^{]+?)(\s+{(?P<field>.+)})?(\s+'(?P<format>[^']+)')?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (xml,             r"xml\s+(?P<url>\S+)\s+(?P<xpath>[^{]+?)(\s+{(?P<field>.+)})?(\s+'(?P<format>[^']+)')?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (jsonxml,         r"json\s+(?P<url>\S+)\s+(?P<xpath>[^{]+?)(\s+{(?P<field>.+)})?(\s+'(?P<format>[^']+)')?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (regex,           r"regex\s+(?P<url>\S+)\s+(?P<regex>.+?)(\s+#(?P<n>\d+))?"),
]
