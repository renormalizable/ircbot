import asyncio
import re
import json
from urllib.parse  import quote_plus, quote, urldefrag
from aiohttp       import request
from lxml          import etree
import lxml.html
import html5lib
from dicttoxml import dicttoxml
import itertools

def drop(l, offset):
    return itertools.islice(l, offset, None)

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
        br.tail = '\n' + (br.tail or '')
    for b in e.xpath('.//b'):
        b.text = '\\x02' + (b.text or '')
        b.tail = '\\x02' + (b.tail or '')
    for i in e.xpath('.//i'):
        i.text = '\\x1d' + (i.text or '')
        i.tail = '\\x1d' + (i.tail or '')
    for u in e.xpath('.//u'):
        u.text = '\\x1f' + (u.text or '')
        u.tail = '\\x1f' + (u.tail or '')
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
        return json.loads(t.decode('utf-8', 'replace'))

class Request:
    def __init__(self):
        pass

    def parsefield(self, field):
        if field:
            # no # in xpath
            f = re.finditer(r"\s*(?P<xpath>[^#]+)?#(?P<field>[^\s']+)?(?:'(?P<format>[^']+)')?", field)
            def getitem(e):
                d = e.groupdict()
                return (d['xpath'] or '.', d['field'] or '', d['format'] if d['format'] else '{}')
            return list(map(getitem, f))
        else:
            return [('.', '', '{}')]

    def getfield(self, get):
        def getl(e, f):
            def gete(e):
                item = get(e, f[1])
                return str(item).strip() if item else ''
            # check if e is node
            l = list(filter(lambda x: any(x), map(gete, e.xpath(f[0], namespaces=self.ns)))) if hasattr(e, 'xpath') else [e]
            return f[2].format(', '.join(l)) if l else ''
        def getf(e):
            return list(map(lambda f: getl(e, f), self.field))
        #return getf
        return (lambda e: list(map(lambda f: getl(e, f), self.field)))

    def parse(self, byte):
        pass

    def get(self, e, f):
        pass

    def format(self, l):
        return map(lambda e: ' '.join(e), l)

    def addns(self, t):
        pass

    @asyncio.coroutine
    def fetch(self, method, url, **kw):
        r = yield from request(method, urldefrag(url)[0], **kw)
        print('get byte')
        try:
            return (yield from r.text())
        except:
            print('bad encoding')
            return (yield from r.read())

    @asyncio.coroutine
    def func(self, get, **kw):
        byte = yield from self.fetch(self.method, self.url, **kw)
        t = self.parse(byte)
        self.addns(t)
        l = t.xpath(self.xpath, namespaces=self.ns)
        #l = self.transform(l)[self.offset:]
        l = drop(self.transform(l), self.offset)
        getf = self.getfield(get)
        return filter(lambda e: any(e), map(getf, l))

    @asyncio.coroutine
    def __call__(self, arg, send, *, method='GET', field=None, transform=None, get=None, format=None, **kw):
        self.n = int(arg.get('n') or 5)
        self.offset = int(arg.get('offset') or 0)
        self.method = method
        self.url = arg['url']
        self.xpath = arg['xpath']
        self.field = field or self.parsefield(arg.get('field'))
        self.transform = transform or (lambda l: l)
        self.ns = {'re': 'http://exslt.org/regular-expressions'}
    
        print(self.field)

        get = get or self.get
        format = format or ((lambda l: map(lambda e: arg['format'].format(*e), l)) if arg.get('format') else self.format)

        l = yield from self.func(get, **kw)
        send(format(l), n=self.n, llimit=10)

class HTMLRequest(Request):
    def parse(self, byte):
        return htmlparse(byte)
    def get(self, e, f):
        if not f:
            return addstyle(e).xpath('string()')
        elif hasattr(e, f):
            return getattr(e, f)
        else:
            return e.attrib.get(f)

html = HTMLRequest()

class XMLRequest(Request):
    def parse(self, byte):
        return xmlparse(byte)
    def get(self, e, f):
        if not f:
            return htmltostr(e.text)
        elif hasattr(e, f):
            return getattr(e, f)
        else:
            return e.attrib.get(f)
    def addns(self, t):
        self.ns.update(t.nsmap)
        xmlns = self.ns.pop(None, None)
        if xmlns:
            self.ns['ns'] = xmlns

xml = XMLRequest()

class JSONRequest(Request):
    def parse(self, byte):
        j = jsonparse(byte)
        #print(j)
        #print(dicttoxml(j))
        return xmlparse(dicttoxml(j))
    def get(self, e, f):
        return e.text

jsonxml = JSONRequest()

#@asyncio.coroutine
#def html(arg, send, *, method='GET', field=None, get=None, transform=None, format=None, **kw):
#    print('html')
#
#    #n = int(arg['n']) if arg['n'] else 5
#    n = int(arg.get('n') or 5)
#    offset = int(arg.get('offset') or 0)
#    url = arg['url']
#    xpath = arg['xpath']
#    #field = field or parsefield(arg['field'])
#    field = field or parsefield(arg.get('field'))
#
#    print(field)
#    ns = {'re': 'http://exslt.org/regular-expressions'}
#    transform = transform or (lambda l: l)
#    get = get or (lambda e, f: addstyle(e).xpath('string()') if f == 'text_content' else getattr(e, f) if hasattr(e, f) else e.attrib.get(f))
#    #formatl = (lambda l: strtoesc(arg['format']).format(*l)) if arg['format'] else (lambda l: ' '.join(l))
#    format = format or ((lambda l: map(lambda e: arg['format'].format(*e), l)) if arg.get('format') else (lambda l: map(lambda e: ' '.join(e), l)))
#
#    @asyncio.coroutine
#    def func(byte):
#        l = htmlparse(byte).xpath(xpath, namespaces=ns)
#        l = transform(l)[offset:]
#        getf = getfield(ns, field, get)
#        l = filter(lambda e: any(e), map(getf, l))
#        #return map(lambda e: formatl(e), l)
#        return format(l)
#
#    return (yield from fetch(method, url, n, func, send, **kw))
#
#@asyncio.coroutine
#def xml(arg, send, *, method='GET', field=None, get=None, transform=None, format=None, **kw):
#    print('xml')
#
#    n = int(arg.get('n') or 5)
#    offset = int(arg.get('offset') or 0)
#    url = arg['url']
#    xpath = arg['xpath']
#    field = field or parsefield(arg.get('field'))
#
#    print(field)
#    ns = {'re': 'http://exslt.org/regular-expressions'}
#    transform = transform or (lambda l: l)
#    get = get or (lambda e, f: htmltostr(e.text) if f == 'text_content' else getattr(e, f) if hasattr(e, f) else e.attrib.get(f))
#    format = format or ((lambda l: map(lambda e: arg['format'].format(*e), l)) if arg.get('format') else (lambda l: map(lambda e: ' '.join(e), l)))
#
#    @asyncio.coroutine
#    def func(byte):
#        t = xmlparse(byte)
#        ns.update(t.nsmap)
#        xmlns = ns.pop(None, None)
#        if xmlns:
#            ns['ns'] = xmlns
#        l = t.xpath(xpath, namespaces=ns)
#        l = transform(l)[offset:]
#        getf = getfield(ns, field, get)
#        l = filter(lambda e: any(e), map(getf, l))
#        return format(l)
#
#    return (yield from fetch(method, url, n, func, send, **kw))
#
#@asyncio.coroutine
#def jsonxml(arg, send, *, method='GET', field=None, get=None, transform=None, format=None, **kw):
#    print('jsonxml')
#
#    n = int(arg.get('n') or 5)
#    offset = int(arg.get('offset') or 0)
#    url = arg['url']
#    xpath = arg['xpath']
#    field = field or parsefield(arg.get('field'))
#
#    print(field)
#    ns = {'re': 'http://exslt.org/regular-expressions'}
#    transform = transform or (lambda l: l)
#    get = get or (lambda e, f: e.text)
#    format = format or ((lambda l: map(lambda e: arg['format'].format(*e), l)) if arg.get('format') else (lambda l: map(lambda e: ' '.join(e), l)))
#
#    @asyncio.coroutine
#    def func(byte):
#        j = jsonparse(byte)
#        #print(j)
#        #print(dicttoxml(j))
#        l = xmlparse(dicttoxml(j)).xpath(xpath, namespaces=ns)
#        l = transform(l)[offset:]
#        getf = getfield(ns, field, get)
#        l = filter(lambda e: any(e), map(getf, l))
#        return format(l)
#
#    return (yield from fetch(method, url, n, func, send, **kw))

@asyncio.coroutine
def regex(arg, send, **kw):
    print('regex')

    n = int(arg.get('n') or 5)
    url = arg['url']

    reg = re.compile(arg['regex'])
    #reg = re.compile(arg['regex'], re.MULTILINE)

    @asyncio.coroutine
    def func(byte):
        print(byte)
        try:
            l = reg.finditer(byte)
        except:
            l = reg.finditer(byte.decode('utf-8', 'replace'))
        return map(lambda e: ', '.join(e.groups()), l)

    return (yield from fetch('GET', url, n, func, send, **kw))


help = [
    ('html'         , 'html <url> <xpath (no { allowed)> [output fields (e.g. {[xpath (no # allowed)]#[attrib][\'format\']})] [#max number][+offset]'),
    ('xml'          , 'xml <url> <xpath (no { allowed)> [output fields (e.g. {[xpath (no # allowed)]#[attrib][\'format\']})] [#max number][+offset]'),
    ('json'         , 'json <url> <xpath (no { allowed)> [output fields (e.g. {[xpath (no # allowed)]#[attrib][\'format\']})] [#max number][+offset]'),
    ('regex'        , 'regex <url> <regex> [#max number][+offset]'),
]

func = [
    # no { in xpath
    (html           , r"html\s+(?P<url>\S+)\s+(?P<xpath>[^{]+?)(\s+{(?P<field>.+)})?(\s+'(?P<format>[^']+)')?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (xml            , r"xml\s+(?P<url>\S+)\s+(?P<xpath>[^{]+?)(\s+{(?P<field>.+)})?(\s+'(?P<format>[^']+)')?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (jsonxml        , r"json\s+(?P<url>\S+)\s+(?P<xpath>[^{]+?)(\s+{(?P<field>.+)})?(\s+'(?P<format>[^']+)')?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (regex          , r"regex\s+(?P<url>\S+)\s+(?P<regex>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
]
