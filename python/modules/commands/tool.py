import asyncio
import itertools
import json
import re
from urllib.parse    import urldefrag

import demjson3 as demjson
import html5lib
import lxml.html
from aiohttp         import ClientSession, ClientRequest
from aiohttp.helpers import parse_mimetype
from dicttoxml       import dicttoxml
from lxml            import etree


demjson.undefined = None

# bad encoding
# https://item.m.jd.com

def drop(l, offset):
    return itertools.islice(l, offset, None)


def charset(r):
    ctype = r.headers.get('content-type', '').lower()
    #_, _, _, params = parse_mimetype(ctype)
    #return params.get('charset')
    return  parse_mimetype(ctype).parameters.get('chardet')


# here we handle timeout differently
async def fetch(method, url, content='text', timeout=10, **kw):
    url_defrag = urldefrag(url)[0]
    # workaround
    req_class = kw.get('request_class', ClientRequest)
    req_kw = kw
    try:
        del req_kw['request_class']
    except KeyError:
        pass

    async with ClientSession(request_class=req_class) as session:
        r = await asyncio.wait_for(session.request(method, url_defrag, **req_kw), timeout)
        print('fetching from {}'.format(r.url))

        if content == 'raw':
            return r
        elif content == 'byte':
            return ((await asyncio.wait_for(r.read(), timeout)), charset(r))
        elif content == 'text':
            # we skip chardet in r.text()
            # as sometimes it yields wrong result
            encoding = charset(r) or 'utf-8'
            text = (await asyncio.wait_for(r.read(), timeout)).decode(encoding, 'replace')
            #try:
            #    text = await asyncio.wait_for(r.text(), timeout)
            #except:
            #    print('bad encoding')
            #    text = (await asyncio.wait_for(r.read(), timeout)).decode('utf-8', 'replace')
            return text

        return None


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
        self.ns = {'re': 'http://exslt.org/regular-expressions'}
        # handy
        self.islice = itertools.islice
        self.iter_first = lambda i: ''.join(itertools.islice(i, 1))
        self.iter_list = lambda i: ', '.join(i)


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
            print('getfield {}'.format(l))
            return f[2].format(', '.join(l)) if l else ''
        return (lambda e: [getf(e, f) for f in field])

    def parse(self, text, encoding):
        pass

    def init_ns(self, t):
        self.ns = {'re': 'http://exslt.org/regular-expressions'}

    def get(self, e, f):
        pass

    def format(self, l):
        return map(lambda e: ' '.join(e), l)

    def get_xpath(self, element, xpath):
        return element.xpath(xpath, namespaces=self.ns)

    def get_field(self, get, element, field):
        #print(field)
        fs = self.get_xpath(element, field[0])
        fs = (get(f, field[1]) for f in fs)
        fs = (f for f in fs if f.strip())
        return field[2](fs)

    def get_fields(self, get, element, fields):
        #print(fields)
        return (self.get_field(get, element, field) for field in fields)

    async def fetch(self, method, url, **kw):
        return (await fetch(method, url, content='byte', **kw))

    async def __call__(self, arg, lines, send, *, method='GET', field=None, transform=None, get=None, preget=None, format=None, format_new=None, **kw):
        n = int(arg.get('n') or 3)
        offset = int(arg.get('offset') or 0)
        try:
            xpath = arg['xpath']
        except KeyError:
            raise Exception('xpath is missing')

        # fetch text
        if lines:
            text = '\n'.join(lines)
            encoding = None
        else:
            try:
                url = arg['url']
            except KeyError:
                raise Exception('url is missing')
            (text, encoding) = await self.fetch(method, url, **kw)
        # parse text into xml
        # text -> tree
        try:
            tree = self.parse(text, encoding)
        except ValueError:
            # handle bad char
            # actually only works with utf-8 encoding
            # https://bpaste.net/show/438a3ef4f0b7
            tree = self.parse(self.rvalid.sub(b'', text), encoding)
        # add xml namespaces to ns
        self.init_ns(tree)
        # find elements
        # tree -> elements
        elements = tree.xpath(xpath, namespaces=self.ns)

        field = field or self.parsefield(arg.get('field'))
        # map elements to elements
        transformer = transform or (lambda es: es)
        # map element to string
        getter_old = get or self.get
        if preget:
            getter = lambda e, f: getter_old(preget(e), f)
        else:
            getter = getter_old
        # map strings to strings
        formatter_old = format or ((lambda l: map(lambda e: arg['format'].format(*e), l)) if arg.get('format') else self.format)
        formatter = (lambda es: format_new(self, es)) if format_new else (lambda es: ([line] for line in formatter_old(filter(lambda e: any(e), map(self.getfield(getter, self.ns, field), transformer(es))))))
        ## transform elements
        #elements = transformer(elements)
        ## get
        #lines = filter(lambda e: any(e), map(self.getfield(getter, ns, field), elements))
        ## format lines
        #lines = formatter_old(lines)

        # format lines
        # elements -> lines
        lines = formatter(elements)
        #print('hello', [list(line) for line in formatter(elements)])
        lines = itertools.chain.from_iterable(itertools.islice(lines, offset, None))
        # send lines
        send(lines, n=n, llimit=10)


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


def htmlget(e, f):
    if hasattr(e, 'xpath'):
        if not f:
            return addstyle(e).xpath('string()')
        elif hasattr(e, f):
            return getattr(e, f, '')
        else:
            return e.attrib.get(f, '')
    else:
        return str(e)


class HTMLRequest(Request):

    def parse(self, text, encoding):
        return htmlparse(text, encoding=encoding)

    def get(self, e, f):
        return htmlget(e, f)

html = HTMLRequest()


def xmlparse(t, encoding=None):
    parser = etree.XMLParser(recover=True, encoding=encoding)
    try:
        return etree.XML(t, parser)
    except:
        return etree.XML(t.encode('utf-8'), parser)


def xmlget(e, f):
    if hasattr(e, 'xpath'):
        if not f:
            return htmltostr(e.text)
        elif hasattr(e, f):
            return getattr(e, f, '')
        else:
            return e.attrib.get(f, '')
    else:
        return str(e)


class XMLRequest(Request):

    def parse(self, text, encoding):
        return xmlparse(text, encoding=encoding)

    def init_ns(self, t):
        self.ns = {'re': 'http://exslt.org/regular-expressions'}
        self.ns.update(t.nsmap)
        xmlns = self.ns.pop(None, None)
        if xmlns:
            self.ns['ns'] = xmlns

    def get(self, e, f):
        return xmlget(e, f)

xml = XMLRequest()


def jsonparse(t, encoding=None):
    try:
        try:
            return json.loads(t)
        except TypeError:
            return json.loads(t.decode(encoding or 'utf-8', 'replace'))
    except:
        return demjson.decode(t, encoding=encoding)


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


async def regex(arg, lines, send, **kw):
    n = int(arg.get('n') or 5)
    url = arg.get('url')

    if arg.get('multi'):
        reg = re.compile(arg['regex'], re.MULTILINE)
    else:
        reg = re.compile(arg['regex'])

    text = '\n'.join(lines) if lines else (await fetch('GET', url, **kw))
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
