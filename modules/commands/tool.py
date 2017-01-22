import asyncio
import re
import json
from urllib.parse    import quote_plus, quote, urldefrag
from aiohttp         import request
from aiohttp.helpers import parse_mimetype
from lxml            import etree
import lxml.html
import html5lib
from dicttoxml import dicttoxml
import demjson
import itertools

demjson.undefined = None

def drop(l, offset):
    return itertools.islice(l, offset, None)

#@asyncio.coroutine
#def fetch(method, url, n, func, send, **kw):
#    print('fetch')
#    #r = yield from asyncio.wait_for(request('GET', urldefrag(url)[0], **kw), 1)
#    r = yield from request(method, urldefrag(url)[0], **kw)
#    #byte = yield from r.read()
#    try:
#        byte = yield from r.text()
#    except:
#        print('bad encoding')
#        byte = yield from r.read()
#    print('get byte')
#    l = yield from func(byte)
#    send(l, n=n, llimit=10)


def charset(r):
    ctype = r.headers.get('content-type', '').lower()
    _, _, _, params = parse_mimetype(ctype)
    return params.get('charset')


@asyncio.coroutine
def fetch(method, url, content='text', **kw):
    print('fetch')
    #h = kw.get('headers')
    #if h:
    #    c = h.get('Connection')
    #    if not c:
    #        h['Connection'] = 'close'
    #else:
    #    kw['headers'] = {'Connection': 'close'}
    r = yield from asyncio.wait_for(request(method, urldefrag(url)[0], **kw), 10)
    #r = yield from request(method, urldefrag(url)[0], **kw)
    print('get byte')
    if content == 'raw':
        return r
    elif content == 'byte':
        return ((yield from r.read()), charset(r))
    elif content == 'text':
        # we skip chardet in r.text()
        # as sometimes it yields wrong result
        encoding = charset(r) or 'utf-8'
        text = (yield from r.read()).decode(encoding, 'replace')
        #try:
        #    text = yield from r.text()
        #except:
        #    print('bad encoding')
        #    text = (yield from r.read()).decode('utf-8', 'replace')
        return text

    return None


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
def htmlparse(t, encoding=None):
    return html5lib.parse(t, treebuilder='lxml', namespaceHTMLElements=False)
    #try:
    #    return html5lib.parse(t, treebuilder='lxml', namespaceHTMLElements=False, transport_encoding=encoding)
    #except TypeError:
    #    return html5lib.parse(t, treebuilder='lxml', namespaceHTMLElements=False)
def htmlparsefast(t, *, parser=None):
    return lxml.html.fromstring(t, parser=parser)


def htmltostr(t):
    return addstyle(htmlparse(t)).xpath('string()')


def xmlparse(t, encoding=None):
    parser = etree.XMLParser(recover=True, encoding=encoding)
    try:
        return etree.XML(t, parser)
    except:
        return etree.XML(t.encode('utf-8'), parser)


def jsonparse(t, encoding=None):
    try:
        try:
            return json.loads(t)
        except TypeError:
            return json.loads(t.decode(encoding or 'utf-8', 'replace'))
    except:
        return demjson.decode(t, encoding=encoding)


class Request:

    def __init__(self):
        # no # in xpath
        self.rfield = re.compile(r"\s*(?P<xpath>[^#]+)?#(?P<field>[^\s']+)?(?:'(?P<format>[^']+)')?")
        # illegal char in xml
        illegal = [
            b"[\x00-\x08]",
            b"[\x0B-\x0C]",
            b"[\x0E-\x1F]",
            b"[\x7F-\x84]",
            b"[\x86-\x9F]",
            b"\xFD[\xD0-\xDF]",
            b"\xFF[\xFE-\xFF]",
            b"\x01\xFF[\xFE-\xFF]",
            b"\x02\xFF[\xFE-\xFF]",
            b"\x03\xFF[\xFE-\xFF]",
            b"\x04\xFF[\xFE-\xFF]",
            b"\x05\xFF[\xFE-\xFF]",
            b"\x06\xFF[\xFE-\xFF]",
            b"\x07\xFF[\xFE-\xFF]",
            b"\x08\xFF[\xFE-\xFF]",
            b"\x09\xFF[\xFE-\xFF]",
            b"\x0A\xFF[\xFE-\xFF]",
            b"\x0B\xFF[\xFE-\xFF]",
            b"\x0C\xFF[\xFE-\xFF]",
            b"\x0D\xFF[\xFE-\xFF]",
            b"\x0E\xFF[\xFE-\xFF]",
            b"\x0F\xFF[\xFE-\xFF]",
            b"\x10\xFF[\xFE-\xFF]",
        ]
        self.rvalid = re.compile(b"(?:" + b"|".join(illegal) + b")+")

    def parsefield(self, field):
        if field:
            def getitem(e):
                d = e.groupdict()
                return (d['xpath'] or '.', d['field'] or '', d['format'] if d['format'] else '{}')
            return [getitem(e) for e in self.rfield.finditer(field)]
        else:
            return [('.', '', '{}')]

    def getfield(self, get, ns, field):
        def getf(e, f):
            #def gete(e):
            #    #item = get(e, f[1])
            #    #return str(item).strip() if item else ''
            #    return str(get(e, f[1]) or '')
            # check if e is node
            #l = [y for y in [gete(x) for x in e.xpath(f[0], namespaces=ns)] if y.strip()] if hasattr(e, 'xpath') else [e]
            l = [y for y in [str(get(x, f[1]) or '') for x in e.xpath(f[0], namespaces=ns)] if y.strip()] if hasattr(e, 'xpath') else [e]
            print(l)
            return f[2].format(', '.join(l)) if l else ''
        return (lambda e: [getf(e, f) for f in field])

    def parse(self, text, encoding):
        pass

    def get(self, e, f):
        pass

    def format(self, l):
        return map(lambda e: ' '.join(e), l)

    def addns(self, t, ns):
        pass

    @asyncio.coroutine
    def fetch(self, method, url, **kw):
        return (yield from fetch(method, url, content='byte', **kw))

    @asyncio.coroutine
    def __call__(self, arg, lines, send, *, method='GET', field=None, transform=None, get=None, preget=None, format=None, **kw):
        n = int(arg.get('n') or 3)
        offset = int(arg.get('offset') or 0)
        method = method
        url = arg.get('url')
        xpath = arg['xpath']
        field = field or self.parsefield(arg.get('field'))
        transform = transform or (lambda l: l)
        ns = {'re': 'http://exslt.org/regular-expressions'}

        print(field)

        getter = get or self.get
        if preget:
            get = lambda e, f: getter(preget(e), f)
        else:
            get = getter
        format = format or ((lambda l: map(lambda e: arg['format'].format(*e), l)) if arg.get('format') else self.format)

        # fetch
        if lines:
            text = '\n'.join(lines)
            encoding = None
        else:
            (text, encoding) = yield from self.fetch(method, url, **kw)
        # parse
        try:
            tree = self.parse(text, encoding)
        except ValueError:
            # handle bad char
            # actually only works with utf-8 encoding
            # https://bpaste.net/show/438a3ef4f0b7
            tree = self.parse(self.rvalid.sub(b'', text), encoding)
        self.addns(tree, ns)
        # find
        l = tree.xpath(xpath, namespaces=ns)
        #l = drop(transform(l), offset)
        l = transform(l)
        # get
        line = filter(lambda e: any(e), map(self.getfield(get, ns, field), l))
        line = drop(line, offset)
        # send
        send(format(line), n=n, llimit=10)


class HTMLRequest(Request):

    def parse(self, text, encoding):
        return htmlparse(text, encoding=encoding)
        #return htmlparse(text.decode(encoding))

    def get(self, e, f):
        if not f:
            return addstyle(e).xpath('string()')
        elif hasattr(e, f):
            return getattr(e, f)
        else:
            return e.attrib.get(f)

html = HTMLRequest()


class XMLRequest(Request):

    def parse(self, text, encoding):
        return xmlparse(text, encoding=encoding)

    def get(self, e, f):
        if not f:
            return htmltostr(e.text)
        elif hasattr(e, f):
            return getattr(e, f)
        else:
            return e.attrib.get(f)

    def addns(self, t, ns):
        ns.update(t.nsmap)
        xmlns = ns.pop(None, None)
        if xmlns:
            ns['ns'] = xmlns

xml = XMLRequest()


class JSONRequest(Request):

    def parse(self, text, encoding):
        #print(text)
        j = jsonparse(text, encoding=encoding)
        b = dicttoxml(j, attr_type=False)
        #print(j)
        #print(b)
        return xmlparse(b)

    def get(self, e, f):
        return e.text

jsonxml = JSONRequest()


@asyncio.coroutine
def regex(arg, lines, send, **kw):
    print('regex')

    n = int(arg.get('n') or 5)
    url = arg.get('url')

    if arg.get('multi'):
        reg = re.compile(arg['regex'], re.MULTILINE)
    else:
        reg = re.compile(arg['regex'])

    text = '\n'.join(lines) if lines else (yield from fetch('GET', url, **kw))
    line = map(lambda e: ', '.join(e.groups()), reg.finditer(text))
    send(line, n=n, llimit=10)


help = [
    #('html'         , 'html (url) <xpath (no { allowed)> [output fields (e.g. {[xpath (no # allowed)]#[attrib][\'format\']})] [#max number][+offset]'),
    #('xml'          , 'xml (url) <xpath (no { allowed)> [output fields (e.g. {[xpath (no # allowed)]#[attrib][\'format\']})] [#max number][+offset]'),
    #('json'         , 'json (url) <xpath (no { allowed)> [output fields (e.g. {[xpath (no # allowed)]#[attrib][\'format\']})] [#max number][+offset]'),
    #('html'         , 'html (url) <xpath> [output fields (e.g. {[xpath]#[attrib][\'format\']})] [#max number][+offset]'),
    #('xml'          , 'xml (url) <xpath> [output fields (e.g. {[xpath]#[attrib][\'format\']})] [#max number][+offset]'),
    #('json'         , 'json (url) <xpath> [output fields (e.g. {[xpath]#[attrib][\'format\']})] [#max number][+offset]'),
    #('regex'        , 'regex (url) <regex> [#max number][+offset]'),
]

func = [
    # no { in xpath
    (html           , r"html(?:\s+(?P<url>http\S+))?\s+(?P<xpath>[^{]+?)(\s+{(?P<field>.+)})?(\s+'(?P<format>[^']+)')?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (xml            , r"xml(?:\s+(?P<url>http\S+))?\s+(?P<xpath>[^{]+?)(\s+{(?P<field>.+)})?(\s+'(?P<format>[^']+)')?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (jsonxml        , r"json(?:\s+(?P<url>http\S+))?\s+(?P<xpath>[^{]+?)(\s+{(?P<field>.+)})?(\s+'(?P<format>[^']+)')?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
    (regex          , r"regex(:(?P<multi>multi)?)?(?:\s+(?P<url>http\S+))?\s+(?P<regex>.+?)(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
]
