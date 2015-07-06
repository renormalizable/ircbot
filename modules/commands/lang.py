import asyncio
import json
import re
from aiohttp          import request
from aiohttp.helpers  import FormData
from urllib.parse     import urlsplit

import config
from .common import Get
from .tool import html, htmlparse, jsonparse, regex

def unsafesend(m, send, *, raw=False):
    if raw:
        l = str(m).splitlines()
        send(l, n=len(l), llimit=16, mlimit=5, raw=True)
    else:
        send(m, mlimit=5)

@asyncio.coroutine
def getcode(url):
    site = {
        'codepad.org':         '/html/body/div/table/tbody/tr/td/div[1]/table/tbody/tr/td[2]/div/pre',
        'paste.ubuntu.com':    '//*[@id="contentColumn"]/div/div/div/table/tbody/tr/td[2]/div/pre',
        'cfp.vim-cn.com':      '.',
        'p.vim-cn.com':        '.',
        'www.fpaste.org':      '//*[@id="paste_form"]/div[1]/div/div[3]',
        'bpaste.net':          '//*[@id="paste"]/div/table/tbody/tr/td[2]/div',
        'pastebin.com':        '//*[@id="paste_code"]',
        'code.bulix.org':      '//*[@id="contents"]/pre',
        'ix.io':               '.',
        'dpaste.com':          '//*[@id="content"]/table/tbody/tr/td[2]/div/pre',
        'ideone.com':          '//*[@id="source"]/pre/ol/li/div',
        'pastebin.com':        '//*[@id="selectable"]/div/ol',
    }

    get = Get()
    u = urlsplit(url)
    xpath = site[u[1]]
    if xpath == '.':
        arg = {'url': url, 'regex': r'(.*)(?:\n|$)', 'n': '0'}
        yield from regex(arg, [], get)
    else:
        arg = {'url': url, 'xpath': xpath, 'n': '0'}
        yield from html(arg, [], get)

    return get.line

@asyncio.coroutine
def clear(arg, lines, send):
    print('clear')

@asyncio.coroutine
def undo(arg, lines, send):
    print('undo')

    n = int(arg['n'] or 1)

    if n < len(lines):
        for i in range(n):
            lines.pop()

        arg['meta']['bot'].addlines(arg['meta']['nick'], lines)

# paste

@asyncio.coroutine
def vimcn(arg, lines, send):
    print('vimcn')

    url = 'https://cfp.vim-cn.com/'
    code = '\n'.join(lines) or arg['code']

    if not code:
        raise Exception()

    data = FormData()
    data.add_field('vimcn', code, content_type='multipart/form-data')
    r = yield from request('POST', url, data=data)

    text = yield from r.text()
    esc = re.compile(r'\x1b[^m]*m')
    text = esc.sub('', text)
    line = text.splitlines()
    send('[\\x0302 {0} \\x0f]'.format(line[0]))

@asyncio.coroutine
def bpaste(arg, lines, send):
    print('bpaste')

    url = 'https://bpaste.net/'
    code = '\n'.join(lines) or arg['code']
    lang = (arg['lang'] or 'text').lower()
    #time = arg['time'] or 'never'
    time = 'never'

    if not code:
        raise Exception()

    d = {
        'clipper':         'Clipper',
        'cucumber':        'Cucumber',
        'robotframework':  'RobotFramework',
    }
    lang = d.get(lang) or lang

    data = {
        'code': code,
        'lexer': lang,
        'expiry': time,
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    r = yield from request('POST', url, data=data, headers=headers)

    send('[\\x0302 {0} \\x0f]'.format(r.url))

@asyncio.coroutine
def rust(arg, lines, send):
    print('rust')

    url = 'https://play.rust-lang.org/evaluate.json'
    code = '\n'.join(lines) or arg['code']
    raw = arg['raw']

    if not code:
        raise Exception()

    data = json.dumps({
        'code': code,
        'color': False,
        'optimize': '3',
        'separate_output': True,
        'test': False,
        'version': 'stable',
    })
    headers = {'Content-Type': 'application/json'}
    r = yield from request('POST', url, data=data, headers=headers)
    byte = yield from r.read()

    j = jsonparse(byte)
    error = j.get('rustc')
    result = j.get('program')
    if error:
        unsafesend('\\x0304error:\\x0f {0}'.format(error), send)
    if result:
        unsafesend(result, send, raw=raw)
    else:
        unsafesend('no output', send, raw=raw)

@asyncio.coroutine
def codepad(arg, lines, send):
    print('codepad')

    url = 'http://codepad.org/'

    alias = {
        'Text':   'Plain Text',
        'Php':    'PHP',
        'Ocaml':  'OCaml',
    }

    code = '\n'.join(lines) or arg['code']
    lang = arg['lang'].title()
    lang = alias.get(lang, lang)
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
        t = htmlparse(byte)
        try:
            result = t.xpath('/html/body/div/table/tbody/tr/td/div[2]/table/tbody/tr/td[2]/div/pre')[0].xpath('string()')
            unsafesend(result, send, raw=raw)
        except IndexError:
            unsafesend('no output', send, raw=raw)
    send('[\\x0302 {0} \\x0f]'.format(r.url))

@asyncio.coroutine
def hackerearth(arg, lines, send):
    print('hackerearth')

    url = 'https://api.hackerearth.com/v3/code/run/'

    alias = {
        'js':               'javascript',
        'py':               'python',
        'rb':               'ruby',
        'hs':               'haskell',
        'pl':               'perl',
        'c++':              'cpp',
        'cxx':              'cpp',
        'c++11':            'cpp11',
        'cxx11':            'cpp11',
        'c#':               'csharp',
    }

    code = '\n'.join(lines) or arg['code']
    lang = arg['lang'].lower()
    lang = alias.get(lang, lang).upper()
    raw = arg['raw']

    if not code:
        raise Exception()

    data = {
        'client_secret': config.key['hackerearth'],
        'lang': lang,
        'source': code,
        'input': '',
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    r = yield from request('POST', url, data=data, headers=headers)
    byte = yield from r.read()
    print(byte)

    j = jsonparse(byte)
    compile = j.get('compile_status')
    result = j.get('run_status').get('output')
    if compile != 'OK':
        unsafesend('\\x0304errors:\\x0f {0}'.format(compile), send)
    if result:
        unsafesend(result, send, raw=raw)
    else:
        unsafesend('no output', send, raw=raw)

@asyncio.coroutine
def rextester(arg, lines, send):
    print('rextester')

    url = 'http://rextester.com/rundotnet/Run'

    default = {
        'c#':               (  1, '', '' ),
        'vb.net':           (  2, '', '' ),
        'f#':               (  3, '', '' ),
        'java':             (  4, '', '' ),
        'python':           (  5, '', '' ),
        'c(gcc)':           (  6, '-o a.out source_file.c', '-Wall -std=gnu99 -O2' ),
        'c++(gcc)':         (  7, '-o a.out source_file.cpp', '-Wall -std=c++11 -O2' ),
        'php':              (  8, '', '' ),
        'pascal':           (  9, '', '' ),
        'objective-c':      ( 10, '-o a.out source_file.m', '' ),
        'haskell':          ( 11, '-o a.out source_file.hs', '' ),
        'ruby':             ( 12, '', '' ),
        'perl':             ( 13, '', '' ),
        'lua':              ( 14, '', '' ),
        'nasm':             ( 15, '', '' ),
        'sql':              ( 16, '', '' ),
        'javascript':       ( 17, '', '' ),
        'lisp':             ( 18, '', '' ),
        'prolog':           ( 19, '', '' ),
        'go':               ( 20, '-o a.out source_file.go', '' ),
        'scala':            ( 21, '', '' ),
        'scheme':           ( 22, '', '' ),
        'node.js':          ( 23, '', '' ),
        'python3':          ( 24, '', '' ),
        'octave':           ( 25, '', '' ),
        'c(clang)':         ( 26, '-o a.out source_file.c', '-Wall -std=gnu99 -O2' ),
        'c++(clang)':       ( 27, '-o a.out source_file.cpp', '-Wall -std=c++11 -O2' ),
        'c++(vc++)':        ( 28, '-o a.exe source_file.cpp', '' ),
        'c(vc)':            ( 29, '-o a.exe source_file.c', '' ),
        'd':                ( 30, '-ofa.out source_file.d', '' ),
        'r':                ( 31, '', '' ),
        'tcl':              ( 32, '', '' ),
    }
    alias = {
        # default
        'c':                'c(gcc)',
        'c++':              'c++(gcc)',
        # rename
        'python2':          'python',
        # abbreviation
        'objc':             'objective-c',
        'asm':              'nasm',
        'vb':               'vb.net',
        'node':             'node.js',
        # extension
        'js':               'javascript',
        'py':               'python',
        'py2':              'python',
        'py3':              'python3',
        'rb':               'ruby',
        'hs':               'haskell',
        'pl':               'perl',
        'cpp':              'c++(gcc)',
        'cxx':              'c++(gcc)',
    }

    code = '\n'.join(lines) or arg['code']
    lang = arg['lang'].lower()
    conf = default.get(alias.get(lang, lang))
    lang = conf[0]
    args = '{0} {1}'.format(conf[1], arg['args'] or conf[2])
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
    stats = j.get('Stats')
    files = j.get('Files')
    if warnings:
        unsafesend('\\x0304warnings:\\x0f {0}'.format(warnings), send)
    if errors:
        unsafesend('\\x0304errors:\\x0f {0}'.format(errors), send)
    if result:
        unsafesend(result, send, raw=raw)
    else:
        unsafesend('no output', send, raw=raw)

@asyncio.coroutine
def python3(arg, lines, send):

    arg.update({
        'lang': 'python3',
        'args': None,
        'raw': None,
    })
    line = [
        'import code',
        'i = code.InteractiveInterpreter()',
        'c = ' + repr(lines + [arg['code']]),
        'b = ""',
        'for l in c:',
        '    b += l + "\\n"',
        '    if not i.runsource(b):',
        '        b = ""',
    ]

    return (yield from rextester(arg, line, send))

@asyncio.coroutine
def haskell(arg, lines, send):

    arg.update({
        'lang': 'haskell',
        'args': '-package ghc',
        'raw': None,
    })
    line = [
        'import GHC',
        'import DynFlags',
        'stmt = [{0}]'.format(', '.join('"{0}"'.format(e) for e in (lines + [arg['code']]))),
        'main = runGhc (Just "/usr/lib/ghc") $ do',
        '    dflags <- getSessionDynFlags',
        '    setSessionDynFlags dflags',
        '    mapM (\s -> runStmt s RunToCompletion) stmt',
    ]
    print(repr(line))

    return (yield from rextester(arg, line, send))

#@asyncio.coroutine
#def ghci(arg, lines, send):
#    print('ghci')
#
#    url = 'http://ghc.io/ghci'
#    code = '\n'.join(lines) or arg['code']
#
#    if not code:
#        raise Exception()
#
#    data = {
#        'data': code,
#    }
#    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
#    r = yield from request('POST', url, data=data, headers=headers)
#    byte = yield from r.read()
#
#    print(byte)
#    j = jsonparse(byte)
#    type = j.get('type')
#    result = j.get('msg')
#    if type == 'error':
#        unsafesend('\\x0304error:\\x0f {0}'.format(result[2]), send)
#    if result:
#        unsafesend(result, send, raw=raw)
#    else:
#        unsafesend('no output', send, raw=raw)

help = [
    ('clear'        , 'clear'),
    ('undo'         , 'undo [number]'),
    ('vimcn'        , 'vimcn (code)'),
    ('bpaste'       , 'bpaste[:lang] (code)'),
    ('rust'         , 'rust (code)'),
    ('codepad'      , 'codepad:<lang> [run] (code)'),
    ('rex'          , 'rex:<lang> [args --] (code)'),
]

func = [
    (clear          , r"clear"),
    (undo           , r"undo(?:\s+(?P<n>\d+))?"),
    (vimcn          , r"vimcn(?:\s+(?P<code>.+))?"),
    (bpaste         , r"bpaste(?::(?P<lang>\S+))?(?:\s+(?P<code>.+))?"),
    (rust           , r"rust(?::(?P<raw>raw))?(?:\s+(?P<code>.+))?"),
    (codepad        , r"codepad:(?P<lang>\S+)(?:\s+(?P<run>run)(?::(?P<raw>raw))?)?(?:\s+(?P<code>.+))?"),
    (hackerearth    , r"hack:(?P<lang>[^\s:]+)(?::(?P<raw>raw))?(?:\s+(?P<code>.+))?"),
    (rextester      , r"rex:(?P<lang>[^\s:]+)(?::(?P<raw>raw))?(?:\s+(?P<args>.+?)\s+--)?(?:\s+(?P<code>.+))?"),
    (python3        , r">> (?P<code>.+)"),
    (haskell        , r"\\\\ (?P<code>.+)"),
]
