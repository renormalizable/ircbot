import asyncio
import json
from aiohttp       import request, TCPConnector
from urllib.parse  import urlsplit

from tool import html, htmlparse, jsonparse

def unsafesend(m, send, *, raw=False):
    if raw:
        l = str(m).splitlines()
        send(l, n=len(l), llimit=16, mlimit=5, raw=True)
    else:
        send(m, mlimit=5)

#class Get:
#    def __init__(self):
#        self.l = ''
#    def __call__(self, m, **kw):
#        self.l += m
class Get:
    def __init__(self):
        self.l = ''
    def __call__(self, l, n=-1, **kw):
        if n < 0:
            self.l += l
        else:
            for (i, m) in enumerate(l):
                if i >= n:
                    break
                self.l += m

@asyncio.coroutine
def getcode(url):
    site = {
        'codepad.org': '/html/body/div/table/tbody/tr/td/div[1]/table/tbody/tr/td[2]/div/pre',
        'paste.ubuntu.com': '//*[@id="contentColumn"]/div/div/div/table/tbody/tr/td[2]/div/pre',
        'cfp.vim-cn.com': '.',
        'p.vim-cn.com': '.',
    }

    get = Get()
    u = urlsplit(url)
    xpath = site.get(u[1])
    if xpath:
        arg = {}
        arg['url'] = url
        arg['xpath'] = xpath
        yield from html(arg, get)
    else:
        raise Exception()
    return get.l + '\n'

@asyncio.coroutine
def clear(arg, lines, send):
    pass

@asyncio.coroutine
def rust(arg, lines, send):
    print('rust')

    url = 'https://play.rust-lang.org/evaluate.json'
    code = lines or arg['code']
    raw = arg['raw']

    if not code:
        raise Exception()

    data = {
        'code': code,
        'optimize': '2',
        'version': 'master',
    }
    headers = {'Content-Type': 'application/json'}
    # ssl has some problem
    conn = TCPConnector(verify_ssl=False)
    r = yield from request('POST', url, data=json.dumps(data), headers=headers, connector=conn)
    byte = yield from r.read()

    result = jsonparse(byte).get('result')
    unsafesend(result, send, raw=raw)

@asyncio.coroutine
def codepad(arg, lines, send):
    print('codepad')

    url = 'http://codepad.org/'
    code = lines or arg['code']
    lang = arg['lang'].title()
    run = bool(arg['run'])
    raw = arg['raw']

    if not code:
        raise Exception()

    data = {
        'lang': lang,
        'code': code,
        'private': 'True',
        'run': str(run),
        'submit': 'Submit',
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    r = yield from request('POST', url, data=data, headers=headers)

    if run:
        byte = yield from r.read()
        result = htmlparse(byte).xpath('/html/body/div/table/tbody/tr/td/div[2]/table/tbody/tr/td[2]/div/pre')[0].xpath('string()')
        unsafesend(result, send, raw=raw)
    send('[\\x0302{0}\\x0f]'.format(r.url))

@asyncio.coroutine
def rextester(arg, lines, send):
    print('rextester')

    url = 'http://rextester.com/rundotnet/api'

    default = {
        'c#':               (  1, '' ),
        'vb.net':           (  2, '' ),
        'f#':               (  3, '' ),
        'java':             (  4, '' ),
        'python':           (  5, '' ),
        'c(gcc)':           (  6, '-Wall -std=gnu99 -O2 -o a.out source_file.c' ),
        'c++(gcc)':         (  7, '-Wall -std=c++11 -O2 -o a.out source_file.cpp' ),
        'php':              (  8, '' ),
        'pascal':           (  9, '' ),
        'objective-c':      ( 10, '-o a.out source_file.m' ),
        'haskell':          ( 11, '-o a.out source_file.hs' ),
        'ruby':             ( 12, '' ),
        'perl':             ( 13, '' ),
        'lua':              ( 14, '' ),
        'nasm':             ( 15, '' ),
        'sql':              ( 16, '' ),
        'javascript':       ( 17, '' ),
        'lisp':             ( 18, '' ),
        'prolog':           ( 19, '' ),
        'go':               ( 20, '-o a.out source_file.go' ),
        'scala':            ( 21, '' ),
        'scheme':           ( 22, '' ),
        'node.js':          ( 23, '' ),
        'python3':          ( 24, '' ),
        'octave':           ( 25, '' ),
        'c(clang)':         ( 26, '-Wall -std=gnu99 -O2 -o a.out source_file.c' ),
        'c++(clang)':       ( 27, '-Wall -std=c++11 -O2 -o a.out source_file.cpp' ),
        'c++(vc++)':        ( 28, '-o a.exe source_file.cpp' ),
        'c(vc)':            ( 29, '-o a.exe source_file.c' ),
        'd':                ( 30, '-ofa.out source_file.d' ),
        'r':                ( 31, '' ),
        'tcl':              ( 32, '' ),
    }
    alias = {
        # default
        'c':                'c(gcc)',
        'c++':              'c++(gcc)',
        # abbreviation
        'objc':             'objective-c',
        'asm':              'nasm',
        'vb':               'vb.net',
        'node':             'node.js',
        'js':               'javascript',
        'py':               'python',
        'py3':              'python3',
        'rb':               'ruby',
        'python2':          'python',
    }

    code = lines or arg['code']
    conf = default.get(alias.get(arg['lang'].lower(), arg['lang'].lower()))
    lang = conf[0]
    args = '{0} {1}'.format(conf[1], arg['args'] or '')
    #input = arg['input'] or ''
    input = ''
    raw = arg['raw']

    if not code:
        raise Exception()

    data = {
        'LanguageChoiceWrapper': lang,
        'Program': code,
        'Input': input,
        'CompilerArgs': args,
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    r = yield from request('POST', url, data=data, headers=headers)
    byte = yield from r.read()

    j = jsonparse(byte)
    warnings = j.get('Warnings')
    errors = j.get('Errors')
    result = j.get('Result')
    if warnings:
        unsafesend('\\x0304warnings:\\x0f {0}'.format(warnings), send)
    if errors:
        unsafesend('\\x0304errors:\\x0f {0}'.format(errors), send)
    if result:
        unsafesend(result, send, raw=raw)

@asyncio.coroutine
def python3(arg, lines, send):
    lines = lines + arg['code']
    arg['lang'] = 'python3'
    arg['args'] = None
    arg['raw'] = None
    return (yield from rextester(arg, lines, send))

help = {
    'clear'          : 'clear',
    'rust'           : 'rust [code, also accept multiline input]',
    'codepad'        : 'codepad:<lang> [run] [code, also accept multiline input]',
    'rex'            : 'rex:<lang> [args --] [code, also accept multiline input]',
}

func = [
    (clear,           r"clear"),
    (rust,            r"rust(?::(?P<raw>raw))?(?:\s+(?P<code>.+))?"),
    (codepad,         r"codepad:(?P<lang>\S+)(?:\s+(?P<run>run)(?::(?P<raw>raw))?)?(?:\s+(?P<code>.+))?"),
    (rextester,       r"rex:(?P<lang>[^\s:]+)(?::(?P<raw>raw))?(?:\s+(?P<args>.+?)\s+--)?(?:\s+(?P<code>.+))?"),
    (python3,         r">> (?P<code>.+)"),
]
