import json
import random
import re
from aiohttp import FormData

from .tool   import fetch, htmlparse, jsonparse

# ruby repl
# https://coliru.stacked-crooked.com/
# TODO geordi newline


def unsafesend(m, send, *, raw=False):
    if raw:
        l = str(m).splitlines()
        send(l, n=len(l), llimit=16, mlimit=1, raw=True)
    else:
        send(m, mlimit=1)

# paste


async def vimcn(arg, lines, send):
    url = 'https://cfp.vim-cn.com/'
    code = '\n'.join(lines) or arg['code'] or ''

    if not code:
        raise Exception()

    data = FormData()
    data.add_field('vimcn', code)
    text = await fetch('POST', url, data=data, content='text')

    esc = re.compile(r'\x1b[^m]*m')
    text = esc.sub('', text)
    line = text.splitlines()
    send('[\\x0302 {0} \\x0f]'.format(line[0]))


async def bpaste(arg, lines, send):
    url = 'https://bpaste.net/'
    code = '\n'.join(lines) or arg['code'] or ''
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
    r = await fetch('POST', url, data=data, headers=headers, content='raw')

    send('[\\x0302 {0} \\x0f]'.format(r.url))

# compiler


async def rust(arg, lines, send):
    #url = 'https://play.rust-lang.org/evaluate.json'
    url = 'https://play.rust-lang.org/execute'
    code = '\n'.join(lines) or arg['code'] or ''
    version = arg['version'] or 'stable'
    raw = arg['raw']

    if not code:
        raise Exception()

    #data = json.dumps({
    #    'backtrace': '0',
    #    'code': code,
    #    'color': False,
    #    'optimize': '0',
    #    'separate_output': True,
    #    'test': False,
    #    'version': version,
    #})
    #headers = {'Content-Type': 'application/json'}
    #byte = (await fetch('POST', url, data=data, headers=headers, content='byte'))[0]

    #j = jsonparse(byte)
    #error = j.get('rustc').split('\n', 1)[1]
    #result = j.get('program')
    #if error:
    #    unsafesend('\\x0304error:\\x0f {0}'.format(error), send)
    #else:
    #    if result:
    #        unsafesend(result, send, raw=raw)
    #    else:
    #        unsafesend('no output', send, raw=raw)
    data = json.dumps({
        'channel': version,
        'code': code,
        'crateType': 'bin',
        'mode': 'debug',
        'tests': False,
        'backtrace': False,
        'edition': '2018',
    })
    headers = {'Content-Type': 'application/json'}
    byte = (await fetch('POST', url, data=data, headers=headers, content='byte'))[0]

    j = jsonparse(byte)
    success = j.get('success')
    error = j.get('stderr').split('\n', 1)[1]
    result = j.get('stdout')
    if not success:
        unsafesend('\\x0304error:\\x0f {0}'.format(error), send)
    else:
        if result:
            unsafesend(result, send, raw=raw)
        else:
            unsafesend('no output', send, raw=raw)


async def rusti32(arg, lines, send):
    url = 'https://play.integer32.com/execute'
    code = '\n'.join(lines) or arg['code'] or ''
    version = arg['version'] or 'stable'
    raw = arg['raw']

    if not code:
        raise Exception()

    data = json.dumps({
        'channel': version,
        'code': code,
        'crateType': 'bin',
        'mode': 'release',
        'tests': False,
    })
    headers = {'Content-Type': 'application/json'}
    byte = (await fetch('POST', url, data=data, headers=headers, content='byte'))[0]

    j = jsonparse(byte)
    success = j.get('success')
    error = j.get('stderr').split('\n', 1)[1]
    result = j.get('stdout')
    if not success:
        unsafesend('\\x0304error:\\x0f {0}'.format(error), send)
    else:
        if result:
            unsafesend(result, send, raw=raw)
        else:
            unsafesend('no output', send, raw=raw)


async def go(arg, lines, send):
    url = 'https://play.golang.org/compile'
    code = '\n'.join(lines) or arg['code'] or ''
    raw = arg['raw']

    if not code:
        raise Exception()

    data = {
        'version': 2,
        'body': code,
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    byte = (await fetch('POST', url, data=data, headers=headers, content='byte'))[0]

    j = jsonparse(byte)
    error = j.get('Errors')
    result = j.get('Events')
    if error:
        unsafesend('\\x0304error:\\x0f {0}'.format(error), send)
    else:
        if result:
            message = result[0].get('Message')
            unsafesend(message, send, raw=raw)
        else:
            unsafesend('no output', send, raw=raw)


async def codepad(arg, lines, send):
    url = 'http://codepad.org/'

    alias = {
        'Text':   'Plain Text',
        'Php':    'PHP',
        'Ocaml':  'OCaml',
    }

    code = '\n'.join(lines) or arg['code'] or ''
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
    r = await fetch('POST', url, data=data, headers=headers, content='raw')

    if run:
        byte = await r.read()
        t = htmlparse(byte)
        try:
            result = t.xpath('/html/body/div/table/tbody/tr/td/div[2]/table/tbody/tr/td[2]/div/pre')[0].xpath('string()')
            unsafesend(result, send, raw=raw)
        except IndexError:
            unsafesend('no output', send, raw=raw)
    send('[\\x0302 {0} \\x0f]'.format(r.url))


async def hackerearth(arg, lines, send):
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

    code = '\n'.join(lines) or arg['code'] or ''
    lang = arg['lang'].lower()
    lang = alias.get(lang, lang).upper()
    raw = arg['raw']

    if not code:
        raise Exception()

    data = {
        'client_secret': arg['meta']['bot'].key['hackerearth'],
        'lang': lang,
        'source': code,
        'input': '',
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    byte = (await fetch('POST', url, data=data, headers=headers, content='byte'))[0]

    j = jsonparse(byte)
    compile = j.get('compile_status')
    result = j.get('run_status').get('output')
    if compile != 'OK':
        unsafesend('\\x0304errors:\\x0f {0}'.format(compile), send)
    else:
        if result:
            unsafesend(result, send, raw=raw)
        else:
            unsafesend('no output', send, raw=raw)


async def hylang(arg, lines, send):
    url = 'https://try-hy.appspot.com/eval'

    code = '\n'.join(lines) or arg['code'] or ''
    raw = False

    if not code:
        raise Exception()

    data = json.dumps({
        'code': code,
        'env': [],
    })
    headers = {'Content-Type': 'application/json'}
    byte = (await fetch('POST', url, data=data, headers=headers, content='byte'))[0]

    j = jsonparse(byte)
    error = j.get('stderr')
    result = j.get('stdout')
    if error:
        unsafesend('\\x0304errors:\\x0f {0}'.format(error), send)
    else:
        if result:
            unsafesend(result, send, raw=raw)
        else:
            unsafesend('no output', send, raw=raw)


async def rextester(arg, lines, send):
    url = 'https://rextester.com/rundotnet/Run'
    #url = 'http://rextester.com/rundotnet/api'

    default = {
        'c#':               (  1, '', '' ),
        'vb.net':           (  2, '', '' ),
        'f#':               (  3, '', '' ),
        'java':             (  4, '', '' ),
        'python':           (  5, '', '' ),
        'c(gcc)':           (  6, '-o a.out source_file.c', '-Wall -std=gnu99 -O2' ),
        'c++(gcc)':         (  7, '-o a.out source_file.cpp', '-Wall -std=c++14 -O2' ),
        'php':              (  8, '', '' ),
        'pascal':           (  9, '', '' ),
        # better way ?
        'objective-c':      ( 10, '-o a.out source_file.m', '-MMD -MP -DGNUSTEP -DGNUSTEP_BASE_LIBRARY=1 -DGNU_GUI_LIBRARY=1 -DGNU_RUNTIME=1 -DGNUSTEP_BASE_LIBRARY=1 -fno-strict-aliasing -fexceptions -fobjc-exceptions -D_NATIVE_OBJC_EXCEPTIONS -pthread -fPIC -Wall -DGSWARN -DGSDIAGNOSE -Wno-import -g -O2 -fgnu-runtime -fconstant-string-class=NSConstantString -I. -I /usr/include/GNUstep -I/usr/include/GNUstep -lobjc -lgnustep-base' ),
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
        'c++(clang)':       ( 27, '-o a.out source_file.cpp', '-Wall -std=c++14 -stdlib=libc++ -O2' ),
        'c++(vc++)':        ( 28, '-o a.exe source_file.cpp', '/EHsc /MD /I C:\boost_1_60_0 /link /LIBPATH:C:\boost_1_60_0\stage\lib' ),
        'c(vc)':            ( 29, '-o a.exe source_file.c', '' ),
        'd':                ( 30, '-ofa.out source_file.d', '' ),
        'r':                ( 31, '', '' ),
        'tcl':              ( 32, '', '' ),
        'mysql':            ( 33, '', '' ),
        'postgresql':       ( 34, '', '' ),
        'oracle':           ( 35, '', '' ),
        # no 36
        'swift':            ( 37, '', '' ),
        'bash':             ( 38, '', '' ),
        'ada':              ( 39, '', '' ),
        'erlang':           ( 40, '', '' ),
        'elixir':           ( 41, '', '' ),
        'ocaml':            ( 42, '', '' ),
    }
    alias = {
        # default
        'c':                'c(gcc)',
        'c++':              'c++(gcc)',
        # rename
        'python2':          'python',
        'shell':            'bash',
        # abbreviation
        'objc':             'objective-c',
        'asm':              'nasm',
        'vb':               'vb.net',
        'node':             'node.js',
        'pgsql':            'postgresql',
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
        'sh':               'bash',
    }

    code = '\n'.join(lines) or arg['code'] or ''
    lang = arg['lang'].lower()

    try:
        conf = default.get(alias.get(lang, lang))
        lang = conf[0]
        args = '{0} {1}'.format(conf[1], arg['args'] or conf[2])
    except:
        raise Exception('Do you REALLY need this language?')

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
        'ShowWarnings': True,
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    byte = (await fetch('POST', url, data=data, headers=headers, content='byte', timeout=30))[0]

    j = jsonparse(byte)
    warnings = j.get('Warnings')
    errors = j.get('Errors')
    result = j.get('Result')
    stats = j.get('Stats')
    files = j.get('Files')
    #if warnings:
    #    unsafesend('\\x0304warnings:\\x0f {0}'.format(warnings), send)
    if errors:
        unsafesend('\\x0304errors:\\x0f {0}'.format(errors), send)
    else:
        if result:
            unsafesend(result, send, raw=raw)
        else:
            unsafesend('no output', send, raw=raw)


# https://wandbox.org seems to be a good alternative to rextester
async def wandbox(arg, lines, send):
    url = 'https://wandbox.org/api/compile.ndjson'

    default = {
        'bash':                 ('bash', '', '', ''),
        'gcc-head-c':           ('gcc-head-c', 'warning,gnu11,cpp-no-pedantic', '', ''),
        'clang-head-c':         ('clang-head-c', 'warning,gnu11,cpp-no-pedantic', '', ''),
        'mono-head':            ('mono-head', '', '', ''),
        'dotnetcore-head':      ('dotnetcore-head', '', '', ''),
        'gcc-head':             ('gcc-head', 'warning,boost-1.68.0-gcc-head,gnu++2a,cpp-no-pedantic', '', ''),
        'clang-head':           ('clang-head', 'warning,boost-1.68.0-clang-head,gnu++2a,cpp-no-pedantic', '', ''),
        # zapcc
        'cmake-head':           ('cmake-head', '', '', ''),
        'gcc-head-pp':          ('gcc-head-pp', 'cpp-p,boost-1.68.0-gcc-head-header', '', ''),
        'clang-head-pp':        ('clang-head-pp', 'cpp-p,boost-1.68.0-clang-head-header', '', ''),
        'coffeescript-head':    ('coffeescript-head', '', '', ''),
        'crystal-head':         ('crystal-head', '', '', ''),
        'dmd-head':             ('dmd-head', '', '', ''),
        'gdc-head':             ('gdc-head', '', '', ''),
        'ldc-head':             ('ldc-head', '', '', ''),
        'elixir-head':          ('elixir-head', '', '', ''),
        'erlang-head':          ('erlang-head', '', '', ''),
        'fsharp-head':          ('fsharp-head', '', '', ''),
        'go-head':              ('go-head', '', '', ''),
        'groovy-head':          ('groovy-head', '', '', ''),
        # ghc-head is broken as of 20181014
        #'ghc-head':             ('ghc-head', 'haskell-warning', '', ''),
        #'ghc-8.4.2':            ('ghc-8.4.2', 'haskell-warning', '', ''),
        #'ghc-head':             ('ghc-head', '', '', ''),
        #'ghc-8.4.2':            ('ghc-8.4.2', '', '', ''),
        'ghc-head':             ('ghc-9.0.1', '', '', ''),
        'ghc-9':                ('ghc-9.0.1', '', '', ''),
        'ghc-8':                ('ghc-8.10.4', '', '', ''),
        'openjdk-head':         ('openjdk-head', '', '', ''),
        'nodejs-head':          ('nodejs-head', '', '', ''),
        # spidermonkey
        'lazyk':                ('lazyk', '', '', ''),
        # clisp
        'sbcl-head':            ('sbcl-head', '', '', ''),
        # lua
        'luajit-head':          ('luajit-head', '', '', ''),
        'nim-head':             ('nim-head', '', '', ''),
        'ocaml-head':           ('ocaml-head', '', '', ''),
        'openssl-head':         ('openssl-head', '', '', ''),
        'php-head':             ('php-head', '', '', ''),
        'fpc-head':             ('fpc-head', '', '', ''),
        'perl-head':            ('perl-head', '', '', ''),
        'pony-head':            ('pony-head', '', '', ''),
        #'cpython-head':         ('cpython-head', '', '', ''),
        #'cpython-2.7-head':     ('cpython-2.7-head', '', '', ''),
        'cpython-head':         ('cpython-3.9.3', '', '', ''),
        'cpython-2.7-head':     ('cpython-2.7.18', '', '', ''),
        'pypy-head':            ('pypy-head', '', '', ''),
        'r-head':               ('r-head', '', '', ''),
        'rill-head':            ('rill-head', '', '', ''),
        'ruby-head':            ('ruby-head', '', '', ''),
        'mruby-head':           ('mruby-head', '', '', ''),
        'rust-head':            ('rust-head', '', '', ''),
        'sqlite-head':          ('sqlite-head', '', '', ''),
        # scala
        'swift-head':           ('swift-head', '', '', ''),
        'vim-head':             ('vim-head', '', '', ''),
    }
    alias = {
        # default
        'c':                'gcc-head-c',
        'c++':              'gcc-head',
        'python':           'cpython-head',
        # rename
        'csharp':           'dotnetcore-head',
        'd':                'gdc-head',
        'haskell':          'ghc-head',
        #'haskell':          'ghc-8.4.2',
        'java':             'openjdk-head',
        'javascript':       'nodejs-head',
        'lua':              'luajit-head',
        'pascal':           'fpc-head',
        'python3':          'cpython-head',
        'python2':          'cpython-2.7-head',
        'shell':            'bash',
        'sql':              'sqlite-head',
        # abbreviation
        # extension
        'js':               'nodejs-head',
        'py':               'cpython-head',
        'py3':              'cpython-head',
        'py2':              'cpython-2.7-head',
        'rb':               'ruby-head',
        'hs':               'ghc-head',
        #'hs':               'ghc-8.4.2',
        'pl':               'perl-head',
        'cpp':              'gcc-head',
        'cxx':              'gcc-head',
        'sh':               'bash',

        # omit -head
        'gcc-c':            'gcc-head-c',
        'clang-c':          'clang-head-c',
        'mono':             'mono-head',
        'dotnetcore':       'dotnetcore-head',
        'gcc':              'gcc-head',
        'clang':            'clang-head',
        # zapcc
        'cmake':            'cmake-head',
        'gcc-pp':           'gcc-head-pp',
        'clang-pp':         'clang-head-pp',
        'coffeescript':     'coffeescript-head',
        'crystal':          'crystal-head',
        'dmd':              'dmd-head',
        'gdc':              'gdc-head',
        'ldc':              'ldc-head',
        'elixir':           'elixir-head',
        'erlang':           'erlang-head',
        'fsharp':           'fsharp-head',
        'go':               'go-head',
        'groovy':           'groovy-head',
        'ghc':              'ghc-head',
        #'ghc':              'ghc-8.4.2',
        'openjdk':          'openjdk-head',
        'nodejs':           'nodejs-head',
        # spidermonkey
        # clisp
        'sbcl':             'sbcl-head',
        # lua
        'luajit':           'luajit-head',
        'nim':              'nim-head',
        'ocaml':            'ocaml-head',
        'openssl':          'openssl-head',
        'php':              'php-head',
        'fpc':              'fpc-head',
        'perl':             'perl-head',
        'pony':             'pony-head',
        'cpython':          'cpython-head',
        'cpython-2.7':      'cpython-2.7-head',
        'pypy':             'pypy-head',
        'r':                'r-head',
        'rill':             'rill-head',
        'ruby':             'ruby-head',
        'mruby':            'mruby-head',
        'rust':             'rust-head',
        'sqlite':           'sqlite-head',
        # scala
        'swift':            'swift-head',
        'vim':              'vim-head',
    }

    arg.setdefault('opts', None)

    code = '\n'.join(lines) or arg['code'] or ''
    lang = arg['lang'].lower()

    try:
        conf = default.get(alias.get(lang, lang))
        # ugly workaround
        conf[0]
    except:
        raise Exception('Do you REALLY need this language?')

    raw = arg['raw']

    if not code:
        raise Exception()

    data = json.dumps({
        'code': code,
        'codes': [],
        'compiler': conf[0],
        #'options': conf[1],
        #'compiler-option-raw': arg['cargs'] or conf[2],
        #'runtime-option-raw': arg['rargs'] or conf[3],
        'options': arg['opts'] or conf[1],
        'compiler-option-raw': arg['args'] or conf[2],
        'runtime-option-raw': conf[3],
        'stdin': '',
    })
    headers = {'Content-Type': 'application/json'}
    text = await fetch('POST', url, data=data, headers=headers, content='text', timeout=30)

    # old api
    #res = []
    #err = []
    ## event source
    #for event in text.split('\r\n'):
    #    line = []
    #    for l in event.split('\n'):
    #        if l.startswith('data: '):
    #            line.append(l[len('data: '):].rstrip('\r'))

    #    if not line:
    #        continue

    #    line = '\n'.join(line)
    #    #print('line', repr(line))

    #    if line.startswith('StdOut:'):
    #        res.append(line[len('StdOut:'):])
    #    elif line.startswith('StdErr:'):
    #        err.append(line[len('StdErr:'):])
    #    elif line.startswith('CompilerMessageE:'):
    #        err.append(line[len('CompilerMessageE:'):])
    #    else:
    #        print('unknown output {0}'.format(repr(line)))

    #if err:
    #    unsafesend('\\x0304errors:\\x0f {0}'.format('\n'.join(err)), send)
    #else:
    #    if res:
    #        unsafesend('\n'.join(res), send, raw=raw)
    #    else:
    #        unsafesend('no output', send, raw=raw)

    # new api
    res = []
    err = []
    # event source
    for event in text.split('\n'):
        if not event:
            continue

        line = json.loads(event)

        if line['type'] == 'StdOut':
            res.append(line['data'])
        elif line['type'] == 'StdErr':
            err.append(line['data'])
        elif line['type'] == 'CompilerMessageE':
            err.append(line['data'])
        else:
            print('unknown output {0}'.format(repr(line)))

    if err:
        unsafesend('\\x0304errors:\\x0f {0}'.format('\n'.join(err)), send)
    else:
        if res:
            unsafesend('\n'.join(res), send, raw=raw)
            #unsafesend('python: ' + '\n'.join(res), send, raw=raw)
        else:
            unsafesend('no output', send, raw=raw)


# repl


async def python3(arg, lines, send):
    arg.update({
        #'lang': 'python3',
        'lang': 'cpython-head',
        'args': None,
        'opts': None,
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

    #return (await rextester(arg, line, send))
    return (await wandbox(arg, line, send))


# TODO file size is too large
# see https://github.com/melpon/wandbox/commit/66c94f1444de2c5598b3c05bfc23429177b759e3
async def haskell(arg, lines, send):
    arg.update({
        #'lang': 'haskell',
        #'lang': 'ghc-8.4.2',
        #'lang': 'ghc-head',
        'lang': 'ghc-8',
        'args': '-package ghc',
        '.4.2opts': None,
        'raw': None,
    })
    # https://github.com/ghc/ghc/blob/master/ghc/InteractiveUI.hs
    # https://github.com/ghc/ghc/blob/master/ghc/GHCi/UI.hs
    # how to support input like 'import Prelude ()' ?
    # currently it cannot unload Prelude functions
    # output stderr ?
    # call stack dump ?
    line = [
        'import GHC',
        #'import DynFlags',
        'import Data.List (isPrefixOf)',
        'import Data.Char (isSpace)',
        # strange bug of rextester
        # we won't get result unless output is long enough
        'stmts :: [[Char]]',
        'stmts = [{0}, "putStrLn . concat . replicate 100000 $ \\" \\""]'.format(', '.join('"{0}"'.format(e.replace('\\', '\\\\').replace('"', '\\"')) for e in (lines + [arg['code']]))),
        #'stmts = [{0}]'.format(', '.join('"{0}"'.format(e.replace('\\', '\\\\').replace('"', '\\"')) for e in (lines + [arg['code']]))),
        'run stmt',
        '    | stmt `looks_like` "import "',
        '    = do ctx <- getContext',
        '         mod <- parseImportDecl stmt',
        '         setContext $ (IIDecl mod) : ctx',
        '    | any (stmt `looks_like`) prefixes = do runDecls stmt; return ()',
        '    | otherwise = do execStmt stmt execOptions; return ()',
        #'    | otherwise = do runStmt stmt SingleStep; return ()',
        '    where s `looks_like` p = p `isPrefixOf` dropWhile isSpace s',
        '          prefixes = [ "class ", "instance ", "data ", "newtype ", "type ", "default ", "default("]',
        #'main = runGhc (Just "/opt/ghc/8.0.1/lib/ghc-8.0.0.20160127/") $ do',
        #'main = runGhc (Just "/usr/lib/ghc") $ do',
        'main = runGhc (Just "/opt/wandbox/ghc-8.4.2/lib/ghc-8.4.2") $ do',
        #'main = runGhc (Just "/opt/wandbox/ghc-head/lib/ghc-8.7.20181121") $ do',
        '    dflags <- getSessionDynFlags',
        '    setSessionDynFlags dflags',
        '    ctx <- getContext',
        '    setContext $ (IIDecl . simpleImportDecl $ mkModuleName "Prelude") : ctx',
        '    mapM run stmts',
    ]
    #print(repr(line))

    #return (await rextester(arg, line, send))
    return (await wandbox(arg, line, send))


#async def ghci(arg, lines, send):
#    url = 'http://ghc.io/ghci'
#    code = '\n'.join(lines) or arg['code'] or ''
#
#    if not code:
#        raise Exception()
#
#    data = {
#        'data': code,
#    }
#    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
#    byte = (await fetch('POST', url, data=data, headers=headers, content='byte'))[0]
#    print(byte)
#
#    j = jsonparse(byte)
#    type = j.get('type')
#    result = j.get('msg')
#    if type == 'error':
#        unsafesend('\\x0304error:\\x0f {0}'.format(result[2]), send)
#    if result:
#        unsafesend(result, send, raw=raw)
#    else:
#        unsafesend('no output', send, raw=raw)


async def rustmain(arg, lines, send):
    arg.update({
        'raw': None,
        'version': 'nightly',
    })
    code = '\n'.join(lines) or arg['code'] or ''
    #line = [
    #    'macro_rules! safe {',
    #    '    ($x:expr) => { println!("expr"); $x };',
    #    '    ($x:stmt) => { println!("stmt"); $x };',
    #    '    ($x:block) => { println!("block"); $x };',
    #    '}',
    #    'macro_rules! safe_rec {',
    #    '    () => {};',
    #    '    ($x:expr; $($y:tt)*) => { $x; safe_rec!($($y)*); };',
    #    '    ($x:stmt; $($y:tt)*) => { $x; safe_rec!($($y)*); };',
    #    '    ($x:block $($y:tt)*) => { $x; safe_rec!($($y)*); };',
    #    '}',
    #    'fn main() {',
    #    '    safe_rec!({});'.format(code),
    #    '}',
    #]
    line = [
        '#![allow(warnings)]',
        '#![feature(core_intrinsics, non_ascii_idents, stmt_expr_attributes)]',
        'fn main() {',
        '    println!("{:?}", {',
        code,
        '    });',
        '}',
    ]

    return (await rust(arg, line, send))


async def rusti32main(arg, lines, send):
    arg.update({
        'raw': None,
        'version': 'nightly',
    })
    code = '\n'.join(lines) or arg['code'] or ''
    line = [
        '#![allow(warnings)]',
        '#![feature(core_intrinsics, non_ascii_idents, stmt_expr_attributes)]',
        'fn main() {',
        '    println!("{:?}", {',
        code,
        '    });',
        '}',
    ]

    return (await rusti32(arg, line, send))


# TODO filter errors 'prog.cc:\d+:\d+: error: (.*)'
async def geordi(arg, lines, send):
    compiler = arg['compiler'] or 'gcc'

    arg.update({
        #'lang': 'c++({})'.format(compiler),
        #'args': '-std=c++1z {}'.format(arg['args'] or ''),
        'lang': '{}-head'.format(compiler),
        #'args': '-std=c++2a -Wno-unused-parameter {}'.format(arg['args'] or '').strip().replace(' ', '\n'),
        #'args': '-std=c++2a {}'.format(arg['args'] or '').strip().replace(' ', '\n'),
        'args': '{0} {1}'.format('-std=c++2b' if compiler == 'gcc' else '-std=c++2b -I/usr/include/c++/5 -I/usr/include/x86_64-linux-gnu/c++/5', arg['args'] or '').strip().replace(' ', '\n'),
        'opts': 'cpp-no-pedantic',
        'raw': None,
    })
 
    line = [
        '#include <bits/stdc++.h>',
        '#include <cxxabi.h>',
        'using namespace std;',
        # comma in ostream
#'''
#template <typename Ch, typename Tr, typename T>
#std::basic_ostream<Ch, Tr> &operator,(std::basic_ostream<Ch, Tr> & o, T const & t) {
#    return o << ", " << t;
#}
#template <typename Ch, typename Tr>
#std::basic_ostream<Ch, Tr> &operator,(std::basic_ostream<Ch, Tr> & o, std::basic_ostream<Ch, Tr> & (* const f) (std::basic_ostream<Ch, Tr> &)) {
#    return o << f;
#}
#''',
#        # bark
#'''
##define BARK (::std::printf(" %s ", __PRETTY_FUNCTION__), ::std::fflush(stdout))
#''',
#        # type
#        #'template <typename Ch, typename Tr, typename T> std::basic_ostream<Ch, Tr> &operator<<(std::basic_ostream<Ch, Tr> & o, type_tag<T>()) { return o << type_string<T>(); }',
#        #'template <typename Ch, typename Tr, typename T> std::basic_ostream<Ch, Tr> &operator<<(std::basic_ostream<Ch, Tr> & o, type_tag<const T>()) { return o << type_string<T>() << " const"; }',
#        #'template <typename Ch, typename Tr, typename T> std::basic_ostream<Ch, Tr> &operator<<(std::basic_ostream<Ch, Tr> & o, type_tag<volatile T>()) { return o << type_string<T>() << " volatile"; }',
#        #'template <typename Ch, typename Tr, typename T> std::basic_ostream<Ch, Tr> &operator<<(std::basic_ostream<Ch, Tr> & o, type_tag<const volatile T>()) { return o << type_string<T>() << " const volatile"; }',
#        #'template <typename T> type_strings_detail::type_tag<T> TYPE() { return type_strings_detail::type_tag<T>(); }',
#'''
#namespace type_strings_detail {
#
#template <typename T>
#std::string type_string() {
#    std::string s = std::type_index(typeid(T)).name();
#    int status = -1;
#    return abi::__cxa_demangle(s.c_str(), 0, 0, &status);
#}
#
#template <typename>
#struct type_tag {};
#
#struct adl_hint {};
#
#template <typename Ch, typename Tr, typename T>
#std::basic_ostream<Ch, Tr> &operator<<(std::basic_ostream<Ch, Tr> & o, adl_hint(type_tag<T>)) {
#    return o << type_string<T>();
#}
#template <typename Ch, typename Tr, typename T>
#std::basic_ostream<Ch, Tr> &operator<<(std::basic_ostream<Ch, Tr> & o, adl_hint(type_tag<const T>)) {
#    return o << type_string<T>() << " const";
#}
#template <typename Ch, typename Tr, typename T>
#std::basic_ostream<Ch, Tr> &operator<<(std::basic_ostream<Ch, Tr> & o, adl_hint(type_tag<volatile T>)) {
#    return o << type_string<T>() << " volatile";
#}
#template <typename Ch, typename Tr, typename T>
#std::basic_ostream<Ch, Tr> &operator<<(std::basic_ostream<Ch, Tr> & o, adl_hint(type_tag<const volatile T>)) {
#    return o << type_string<T>() << " const volatile";
#}
#
#}
#
#template <typename T>
#type_strings_detail::adl_hint TYPE(type_strings_detail::type_tag<T>) {
#    return type_strings_detail::adl_hint();
#}
#''',
#        # type desc
##template <typename>
##struct type_desc;
##
###define BUILTIN_TYPE_DESC(type, desc)              \
##    template <> struct type_desc<type> {           \
##        static std::string str() { return desc; }  \
##    }
##
##BUILTIN_TYPE_DESC(void, "void");
##BUILTIN_TYPE_DESC(bool, "boolean");
##BUILTIN_TYPE_DESC(char, "character");
##BUILTIN_TYPE_DESC(signed char, "singed character");
##BUILTIN_TYPE_DESC(unsigned char, "unsigned character");
##BUILTIN_TYPE_DESC(short, "short integer");
##BUILTIN_TYPE_DESC(unsigned short, "unsigned short integer");
##BUILTIN_TYPE_DESC(int, "integer");
##BUILTIN_TYPE_DESC(unsigned int, "unsigned integer");
##BUILTIN_TYPE_DESC(long, "long integer");
##BUILTIN_TYPE_DESC(unsigned long, "unsigned long integer");
#'''
#namespace type_desc_detail {
#
#template <typename T>
#struct type_desc {
#    static std::string str() {
#        std::string s = std::type_index(typeid(T)).name();
#        int status = -1;
#        return abi::__cxa_demangle(s.c_str(), 0, 0, &status);
#    }
#};
#
#template <typename T>
#struct type_desc<const T> {
#    static std::string str() {
#        return "constant " + type_desc<T>::str();
#    }
#};
#
#template <typename T>
#struct type_desc<volatile T> {
#    static std::string str() {
#        return "volatile " + type_desc<T>::str();
#    }
#};
#
#template <typename T>
#struct type_desc<const volatile T> {
#    static std::string str() {
#        return "constant volatile " + type_desc<T>::str();
#    }
#};
#
#template <typename T>
#struct type_desc<T*> {
#    static std::string str() {
#        return "pointer to " + type_desc<T>::str();
#    }
#};
#
#template <typename T>
#struct type_desc<T&> {
#    static std::string str() {
#        return "lvalue reference to " + type_desc<T>::str();
#    }
#};
#
#template <typename T>
#struct type_desc<T&&> {
#    static std::string str() {
#        return "rvalue reference to " + type_desc<T>::str();
#    }
#};
#
#
#template <typename R>
#struct type_desc<R()> {
#    static std::string str() {
#        return "function taking void returning " + type_desc<R>::str();
#    }
#};
#
#template <typename R, typename... Ts>
#struct type_desc<R(Ts...)> {
#    static std::string str() {
#        std::vector<std::string> svec = {type_desc<Ts>::str()...};
#
#        std::string flat;
#        bool first = true;
#        for (const auto& s : svec) {
#            if (first) {
#                first = false;
#                flat += s;
#            } else {
#                flat += ", " + s;
#            }
#        }
#
#        return "function taking " + flat + " returning " + type_desc<R>::str();
#    }
#};
#
#}
#
#
#template <typename T>
#type_desc_detail::type_desc<T> TYPE_DESC() {
#    return {};
#}
#
#
#template <typename Ch, typename Tr, typename T>
#std::basic_ostream<Ch, Tr>& operator<<(std::basic_ostream<Ch, Tr>& os, type_desc_detail::type_desc<T>()) {
#    return os << type_desc_detail::type_desc<T>::str();
#}
#''',
#'''
##define GENERATE_CONTAINER_PRINT(C)                                            \
#    template <typename Ch, typename Tr, typename T, typename Allocator>        \
#    std::basic_ostream<Ch, Tr>& operator<<(std::basic_ostream<Ch, Tr>& o,      \
#                                           const C<T, Allocator>& container) { \
#        o << "[";                                                              \
#        bool first = true;                                                     \
#        for (const auto& c : container) {                                      \
#            if (first) {                                                       \
#                first = false;                                                 \
#                o << c;                                                        \
#            } else {                                                           \
#                o << ", " << c;                                                \
#            }                                                                  \
#        }                                                                      \
#        return o << "]";                                                       \
#    }
#
#GENERATE_CONTAINER_PRINT(std::vector)
#GENERATE_CONTAINER_PRINT(std::list)
#
#template <typename Ch, typename Tr, typename T, std::size_t N,
#          typename U = std::remove_cv_t<std::remove_reference_t<T>>,
#          std::enable_if_t<
#              !std::is_same_v<U, char> && !std::is_same_v<U, wchar_t>, int> = 0>
#std::basic_ostream<Ch, Tr>& operator<<(std::basic_ostream<Ch, Tr>& o,
#                                       T (&a)[N]) {
#    std::vector<T> vec(std::begin(a), std::end(a));
#    return o << vec;
#}
#
#template <typename Ch, typename Tr, typename T1, typename T2>
#std::basic_ostream<Ch, Tr>& operator<<(std::basic_ostream<Ch, Tr>& o,
#                                       const std::pair<T1, T2>& pr) {
#    return o << "(" << pr.first << ", " << pr.second << ")";
#}
#
#namespace detail {
#template <typename Ch, typename Tr, typename... Ts>
#void print_tuple(std::basic_ostream<Ch, Tr>& o, const std::tuple<Ts...>& tp,
#                 std::index_sequence<>, bool first = true) {}
#
#template <typename Ch, typename Tr, typename... Ts, std::size_t I,
#          std::size_t... Is>
#void print_tuple(std::basic_ostream<Ch, Tr>& o, const std::tuple<Ts...>& tp,
#                 std::index_sequence<I, Is...>, bool first = true) {
#    if (first) {
#        o << std::get<I>(tp);
#        first = false;
#    } else {
#        o << ", " << std::get<I>(tp);
#    }
#
#    print_tuple(o, tp, std::index_sequence<Is...>{}, first);
#}
#} // namespace detail
#
#template <typename Ch, typename Tr, typename... Ts>
#std::basic_ostream<Ch, Tr>& operator<<(std::basic_ostream<Ch, Tr>& o,
#                                       const std::tuple<Ts...>& tp) {
#    o << "(";
#    detail::print_tuple(o, tp, std::index_sequence_for<Ts...>{});
#    return o << ")";
#}
#''',

'''
namespace tracked {
namespace detail {
class Tracked {
protected:
    Tracked();
    Tracked(Tracked const&);
    Tracked(Tracked&&);
    void operator=(Tracked const&);
    void operator=(Tracked&&);
    ~Tracked();
    void set_name(char const*) const;
};
} // namespace detail
struct B : protected detail::Tracked {
    B();
    B(B const&);
    B(B&&);
    B& operator=(B const&);
    B& operator=(B&&);
    virtual ~B();
    void* operator new(std::size_t);
    void* operator new[](std::size_t);
    void* operator new(std::size_t, std::nothrow_t const&) throw();
    void* operator new[](std::size_t, std::nothrow_t const&) throw();
    void* operator new(std::size_t const, void* const p) throw() {
        return p;
    }
    void* operator new[](std::size_t const, void* const p) throw() {
        return p;
    }
    void operator delete(void*, std::size_t) throw();
    void operator delete[](void*, std::size_t) throw();
    void f() const;
    virtual void vf() const;
    B& operator++();
    B operator++(int);
    void operator*() const;
    friend std::ostream& operator<<(std::ostream& os, const B&);
private:
    void print(std::ostream&) const;
};
struct D : B {
    D();
    D(D const&);
    D(D&&);
    D& operator=(D const&);
    D& operator=(D&&);
    ~D();
    void* operator new(std::size_t);
    void* operator new[](std::size_t);
    void* operator new(std::size_t, std::nothrow_t const&) throw();
    void* operator new[](std::size_t, std::nothrow_t const&) throw();
    void* operator new(std::size_t const, void* const p) throw() {
        return p;
    }
    void* operator new[](std::size_t const, void* const p) throw() {
        return p;
    }
    void operator delete(void*, std::size_t) throw();
    void operator delete[](void*, std::size_t) throw();
    void operator delete(void*) throw() {}
    void f() const;
    virtual void vf() const;
    friend std::ostream& operator<<(std::ostream&, const D&);
private:
    void print(std::ostream&) const;
};
} // namespace tracked
namespace tracked {
namespace detail {
enum Status { fresh, pillaged, destructed };
struct Entry {
    Tracked const* p;
    char const* name;
    Status status;
};
typedef std::vector<Entry> Entries;
Entries& entries() {
    static Entries* p = new Entries;
    return *p;
}
// Keeping track of Trackeds outside of the objects themselves allows us to give
// nice diagnostics for operations on objects that have already perished.
// Invariant: If multiple entries have identical p, then all but the last have
// status==destructed. Todo: not good enough
std::ptrdiff_t id(Entry const& e) {
    return &e - &entries().front();
}
void print(Entry const& e) {
    std::printf("%s%lu", e.name, id(e));
}
Entry* entry(Tracked const* const r) {
    for (Entries::reverse_iterator i(entries().rbegin()); i != entries().rend();
         ++i)
        if (i->p == r)
            return &*i;
    return 0;
}
std::ptrdiff_t id(Tracked const& t) {
    return id(*entry(&t));
}
std::ostream& operator<<(std::ostream& o, Entry const& e) {
    return o << e.name << id(e);
}
void make_entry(Tracked const* const r) {
    if (Entry* const e = entry(r))
        if (e->status != destructed)
            std::cerr << "leaked: " << *e << '.';
    Entry const e = {r, "?", fresh};
    entries().push_back(e);
}
void assert_status_below(Tracked const* const r, Status const st,
                         std::string const& s) {
    Entry* const e = entry(r);
    if (!e)
        std::cerr << "tried to " << s << " non-existent object.";
    if (e->status < st)
        return;
    std::cerr << "tried to " << s
              << (e->status == pillaged ? " pillaged " : " destructed ") << *e
              << '.';
}
void* op_new(std::size_t, bool const array, void* const r,
             char const* const name) {
    if (!r)
        return 0;
    std::cout << "new(" << name << (array ? "[]" : "") << ")";
    std::cout << ' ';
    return r;
}
void op_delete(void* const p, std::size_t const s) {
    ::operator delete(p);
    for (Entries::const_iterator j = entries().begin(); j != entries().end();
         ++j)
        if (p <= j->p &&
            static_cast<void const*>(j->p) <= static_cast<char*>(p) + s) {
            std::cout << "delete(" << *j << ")";
            std::cout << ' ';
            return;
        }
}
void op_array_delete(void* const p, std::size_t const s) {
    ::operator delete[](p);
    std::cout << "delete[";
    bool first = true;
    for (Entries::const_iterator j = entries().begin(); j != entries().end();
         ++j)
        if (p <= j->p &&
            static_cast<void const*>(j->p) <= static_cast<char*>(p) + s) {
            if (first) {
                first = false;
            } else
                std::cout << ", ";
            std::cout << *j;
        }
    std::cout << ']';
    std::cout << ' ';
}
void Tracked::set_name(char const* const s) const {
    entry(this)->name = s;
}
Tracked::Tracked() {
    make_entry(this);
}
Tracked::Tracked(Tracked const& i) {
    assert_status_below(&i, pillaged, "copy");
    make_entry(this);
}
void Tracked::operator=(Tracked const& r) {
    assert_status_below(this, destructed, "assign to");
    assert_status_below(&r, pillaged, "assign from");
    entry(this)->status = fresh;
}
Tracked::Tracked(Tracked&& r) {
    assert_status_below(&r, pillaged, "move");
    make_entry(this);
    entry(&r)->status = pillaged;
}
void Tracked::operator=(Tracked&& r) {
    assert_status_below(this, destructed, "move-assign to");
    assert_status_below(&r, pillaged, "move");
    entry(this)->status = fresh;
    entry(&r)->status = pillaged;
}
Tracked::~Tracked() {
    assert_status_below(this, destructed, "re-destruct");
    entry(this)->status = destructed;
}
} // namespace detail
// B:
B::B() {
    set_name("B");
    print(std::cout);
    std::cout << '*';
    std::cout << ' ';
}
B::B(B const& b) : Tracked(b) {
    set_name("B");
    print(std::cout);
    std::cout << "*(";
    b.print(std::cout);
    std::cout << ')';
    std::cout << ' ';
}
B& B::operator=(B const& b) {
    Tracked::operator=(b);
    print(std::cout);
    std::cout << '=';
    b.print(std::cout);
    std::cout << ' ';
    return *this;
}
B::~B() {
    assert_status_below(this, detail::destructed, "destruct");
    print(std::cout);
    std::cout << '~';
    std::cout << ' ';
}
void* B::operator new(std::size_t const s) {
    return detail::op_new(s, false, ::operator new(s), "B");
}
void* B::operator new[](std::size_t const s) {
    return detail::op_new(s, true, ::operator new[](s), "B");
}
void* B::operator new(std::size_t const s, std::nothrow_t const& t) throw() {
    return detail::op_new(s, false, ::operator new(s, t), "B");
}
void* B::operator new[](std::size_t const s, std::nothrow_t const& t) throw() {
    return detail::op_new(s, true, ::operator new[](s, t), "B");
}
void B::operator delete(void* const p, std::size_t const s) throw() {
    detail::op_delete(p, s);
}
void B::operator delete[](void* const p, std::size_t const s) throw() {
    detail::op_array_delete(p, s);
}
void B::f() const {
    assert_status_below(this, detail::pillaged, "call B::f() on");
    print(std::cout);
    std::cout << ".f()";
    std::cout << ' ';
}
void B::vf() const {
    assert_status_below(this, detail::pillaged, "call B::vf() on");
    print(std::cout);
    std::cout << ".vf()";
    std::cout << ' ';
}
B::B(B&& b) : Tracked(std::move(b)) {
    set_name("B");
    b.print(std::cout);
    std::cout << "=>";
    print(std::cout);
    std::cout << '*';
    std::cout << ' ';
}
B& B::operator=(B&& b) {
    Tracked::operator=(std::move(b));
    b.print(std::cout);
    std::cout << "=>";
    print(std::cout);
    std::cout << ' ';
    return *this;
}
B& B::operator++() {
    assert_status_below(this, detail::pillaged, "pre-increment");
    std::cout << "++";
    print(std::cout);
    std::cout << ' ';
    return *this;
}
B B::operator++(int) {
    assert_status_below(this, detail::pillaged, "post-increment");
    B const r(*this);
    operator++();
    return r;
}
void B::operator*() const {
    assert_status_below(this, detail::pillaged, "dereference");
    std::cout << '*';
    print(std::cout);
    std::cout << ' ';
}
void B::print(std::ostream& o) const {
    o << 'B' << id(*this);
}
std::ostream& operator<<(std::ostream& o, B const& b) {
    assert_status_below(&b, detail::pillaged, "read");
    b.print(o);
    return o;
}
// D:
D::D() {
    set_name("D");
    print(std::cout);
    std::cout << '*';
    std::cout << ' ';
}
D::D(D const& d) : B(d) {
    set_name("D");
    print(std::cout);
    std::cout << "*(";
    d.print(std::cout);
    std::cout << ')';
    std::cout << ' ';
}
D& D::operator=(D const& d) {
    B::operator=(d);
    print(std::cout);
    std::cout << '=';
    d.print(std::cout);
    std::cout << ' ';
    return *this;
}
D::~D() {
    assert_status_below(this, detail::destructed, "destruct");
    print(std::cout);
    std::cout << '~';
    std::cout << ' ';
}
void* D::operator new(std::size_t const s) {
    return detail::op_new(s, false, ::operator new(s), "D");
}
void* D::operator new[](std::size_t const s) {
    return detail::op_new(s, true, ::operator new[](s), "D");
}
void* D::operator new(std::size_t const s, std::nothrow_t const& t) throw() {
    return detail::op_new(s, false, ::operator new(s, t), "D");
}
void* D::operator new[](std::size_t const s, std::nothrow_t const& t) throw() {
    return detail::op_new(s, true, ::operator new[](s, t), "D");
}
void D::operator delete(void* const p, std::size_t const s) throw() {
    detail::op_delete(p, s);
}
void D::operator delete[](void* const p, std::size_t const s) throw() {
    detail::op_array_delete(p, s);
}
void D::f() const {
    assert_status_below(this, detail::pillaged, "call D::f() on");
    print(std::cout);
    std::cout << ".f()";
    std::cout << ' ';
}
void D::vf() const {
    assert_status_below(this, detail::pillaged, "call D::vf() on");
    print(std::cout);
    std::cout << ".vf()";
    std::cout << ' ';
}
void D::print(std::ostream& o) const {
    o << 'D' << id(*this);
}
std::ostream& operator<<(std::ostream& o, D const& d) {
    assert_status_below(&d, detail::pillaged, "read");
    d.print(o);
    std::cout << ' ';
    return o;
}
D::D(D&& d) : B(std::move(d)) {
    set_name("D");
    d.print(std::cout);
    std::cout << "=>";
    print(std::cout);
    std::cout << '*';
    std::cout << ' ';
}
D& D::operator=(D&& d) {
    B::operator=(std::move(d));
    d.print(std::cout);
    std::cout << ' ';
    std::cout << "=>";
    print(std::cout);
    std::cout << ' ';
    return *this;
}
// In the above, it looks like there is a lot of code duplication for B and D.
// Previous implementations of these tracking facilities used clever CRTP helper
// templates to factor out as much of the common code as possible. However, to
// prevent the cleverness from showing through in gcc diagnostics, small
// delegators had to be put in B/D for all operations (in addition to the ones
// for the constructors which were always there, since constructors cannot be
// inherited (yet)). In the end, the hassle was not worth the gain, so I
// reverted back to the simple straightforward approach.
void atexit() {
    bool first = true;
    for (detail::Entries::const_iterator i = detail::entries().begin();
         i != detail::entries().end(); ++i)
        if (i->status != detail::destructed) {
            if (first) {
                std::printf("leaked: ");
                first = false;
            } else {
                std::printf(", ");
            }
            print(*i);
        }
    if (!first) {
        std::printf(".");
        abort();
    }
}
} // namespace tracked
'''
    ]
    # not correct but maybe enough?
    #if '++14' in arg['args'] or '++1y' in arg['args']:
    #    line = [
    #        # experimental
    #        '#include <experimental/string_view>',
    #        '#include <experimental/optional>',
    #    ] + line

    printing = re.compile(r'<<(?P<print>.+?)(?:;(?P<code>.*))?', re.DOTALL)
    statement = re.compile(r'{{(?P<main>.+?)}}(?P<code>.*)?', re.DOTALL)

    p = printing.fullmatch(arg['code'])
    if p:
        p = p.groupdict()
        line.extend([
            p['code'] or '',
            #'int main() {{ std::cout << {}; std::cout << std::endl; return 0; }}'.format(p['print']),
            'int main(int argc, char* argv[], char* env[]) {{ std::cout << {}; std::cout << std::endl; return 0; }}'.format(p['print']),
        ])
        #print(line)
        #return (await rextester(arg, line, send))
        return (await wandbox(arg, line, send))

    s = statement.fullmatch(arg['code'])
    if s:
        s = s.groupdict()
        line.extend([
            s['code'] or '',
            #'int main() {{ {} }}'.format(s['main']),
            'int main(int argc, char* argv[], char* env[]) {{ {} }}'.format(s['main']),
        ])
        #print(line)
        #return (await rextester(arg, line, send))
        return (await wandbox(arg, line, send))

    line.append(arg['code'])
    #print(line)

    #return (await rextester(arg, line, send))
    return (await wandbox(arg, line, send))


# leetcode


async def leetcode(arg, lines, send):
    url = 'https://leetcode.com/api/problems/all/'

    byte = (await fetch('GET', url, content='byte'))[0]
    j = jsonparse(byte)

    if arg['id'] == None:
        if arg['difficulty'] == None:
            problem = random.choice(j.get('stat_status_pairs'))
        else:
            di = {
                'easy': 1,
                'medium': 2,
                'hard': 3,
            }[arg['difficulty']]
            problem = random.choice([x for x in j.get('stat_status_pairs') if x.get('difficulty').get('level') == di])
    else:
        id = int(arg['id'])
        problem = [x for x in j.get('stat_status_pairs') if x.get('stat').get('frontend_question_id') == id][0]

    stat = problem.get('stat')
    difficulty = {
        1: 'easy',
        2: 'medium',
        3: 'hard',
    }[problem.get('difficulty').get('level')]

    send('#{0} [\\x0302 https://leetcode.com/problems/{1}/ \\x0f] {2} / {3} AC / {4}%'.format(stat.get('frontend_question_id'), stat.get('question__title_slug'), difficulty, stat.get('total_acs'), round(100 * stat.get('total_acs') / stat.get('total_submitted'))))


help = [
    ('vimcn'        , 'vimcn (code)'),
    ('bpaste'       , 'bpaste[:lang] (code)'),
    ('rust'         , 'rust (code)'),
    ('go'           , 'go (code)'),
    ('codepad'      , 'codepad:<lang> [run] (code)'),
    ('rex'          , 'rex:<lang> [args --] (code)'),
    ('wand'         , 'wand:<lang> [args --] (code)'),
]

func = [
    (vimcn          , r"vimcn(?:\s+(?P<code>.+))?"),
    (bpaste         , r"bpaste(?::(?P<lang>\S+))?(?:\s+(?P<code>.+))?"),
    #(rust           , r"rust(?::(?P<version>stable|beta|nightly))?(?::(?P<raw>raw))?(?:\s+(?P<code>.+))?"),
    #(rusti32        , r"rusti32(?::(?P<version>stable|beta|nightly))?(?::(?P<raw>raw))?(?:\s+(?P<code>.+))?"),
    #(go             , r"go(?::(?P<raw>raw))?(?:\s+(?P<code>.+))?"),
    (codepad        , r"codepad:(?P<lang>\S+)(?:\s+(?P<run>run)(?::(?P<raw>raw))?)?(?:\s+(?P<code>.+))?"),
    (hackerearth    , r"hack:(?P<lang>[^\s:]+)(?::(?P<raw>raw))?(?:\s+(?P<code>.+))?"),
    (rextester      , r"rex:(?P<lang>[^\s:]+)(?::(?P<raw>raw))?(?:\s+(?P<args>.+?)\s+--)?(?:\s+(?P<code>.+))?"),
    #(wandbox        , r"wand:(?P<lang>[^\s:]+)(?::(?P<raw>raw))?(?:\s+(?P<args>.+?)\s+--)?(?:\s+(?P<code>.+))?"),
    (hylang         , r"hy(?:\s+(?P<code>.+))?"),
    #(python3        , r">> (?P<code>.+)"),
    #(python3        , r"py (?P<code>.+)"),
    (haskell        , r"\\\\ (?P<code>.+)"),
    #(rustmain       , r"rs (?P<code>.+)"),
    #(rusti32main    , r"rsi32 (?P<code>.+)"),
    #(geordi         , r"geordi(?::(?P<compiler>gcc|clang))?(?:\s+(?P<args>.+?)\s+--)?(?:\s+(?P<code>.+))?"),
    #(leetcode       , r"leetcode(?:(?:\s+#(?P<id>\d+))|(?:\s+(?P<difficulty>easy|medium|hard)))?"),
]
