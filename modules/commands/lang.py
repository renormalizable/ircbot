import asyncio
import json
import re
from aiohttp import FormData

from .tool import fetch, htmlparse, jsonparse


def unsafesend(m, send, *, raw=False):
    if raw:
        l = str(m).splitlines()
        send(l, n=len(l), llimit=16, mlimit=1, raw=True)
    else:
        send(m, mlimit=1)

# paste


@asyncio.coroutine
def vimcn(arg, lines, send):
    print('vimcn')

    url = 'https://cfp.vim-cn.com/'
    code = '\n'.join(lines) or arg['code'] or ''

    if not code:
        raise Exception()

    data = FormData()
    data.add_field('vimcn', code)
    text = yield from fetch('POST', url, data=data, content='text')

    esc = re.compile(r'\x1b[^m]*m')
    text = esc.sub('', text)
    line = text.splitlines()
    send('[\\x0302 {0} \\x0f]'.format(line[0]))


@asyncio.coroutine
def bpaste(arg, lines, send):
    print('bpaste')

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
    r = yield from fetch('POST', url, data=data, headers=headers, content='raw')

    send('[\\x0302 {0} \\x0f]'.format(r.url))

# compiler


@asyncio.coroutine
def rust(arg, lines, send):
    print('rust')

    url = 'https://play.rust-lang.org/evaluate.json'
    code = '\n'.join(lines) or arg['code'] or ''
    version = arg['version'] or 'stable'
    raw = arg['raw']

    if not code:
        raise Exception()

    data = json.dumps({
        'backtrace': '0',
        'code': code,
        'color': False,
        'optimize': '3',
        'separate_output': True,
        'test': False,
        'version': version,
    })
    headers = {'Content-Type': 'application/json'}
    r = yield from fetch('POST', url, data=data, headers=headers, content='raw')
    byte = yield from r.read()

    j = jsonparse(byte)
    error = j.get('rustc').split('\n', 1)[1]
    result = j.get('program')
    if error:
        unsafesend('\\x0304error:\\x0f {0}'.format(error), send)
    else:
        if result:
            unsafesend(result, send, raw=raw)
        else:
            unsafesend('no output', send, raw=raw)


@asyncio.coroutine
def rusti32(arg, lines, send):
    print('rusti32')

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
    r = yield from fetch('POST', url, data=data, headers=headers, content='raw')
    byte = yield from r.read()

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


@asyncio.coroutine
def go(arg, lines, send):
    print('go')

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
    r = yield from fetch('POST', url, data=data, headers=headers, content='raw')
    byte = yield from r.read()

    print(byte)
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


@asyncio.coroutine
def codepad(arg, lines, send):
    print('codepad')

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
    r = yield from fetch('POST', url, data=data, headers=headers, content='raw')

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
    r = yield from fetch('POST', url, data=data, headers=headers, content='raw')
    byte = yield from r.read()
    print(byte)

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


@asyncio.coroutine
def hylang(arg, lines, send):
    print('hylang')

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
    r = yield from fetch('POST', url, data=data, headers=headers, content='raw')
    byte = yield from r.read()
    print(byte)

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


@asyncio.coroutine
def rextester(arg, lines, send):
    print('rextester')

    url = 'http://rextester.com/rundotnet/Run'
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
    r = yield from fetch('POST', url, data=data, headers=headers, content='raw')
    byte = yield from r.read()

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

# repl


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
    # https://github.com/ghc/ghc/blob/master/ghc/InteractiveUI.hs
    # https://github.com/ghc/ghc/blob/master/ghc/GHCi/UI.hs
    # how to support input like 'import Prelude ()' ?
    # currently it cannot unload Prelude functions
    # output stderr ?
    # call stack dump ?
    line = [
        'import GHC',
        'import DynFlags',
        'import Data.List (isPrefixOf)',
        'import Data.Char (isSpace)',
        # strange bug of rextester
        # we won't get result unless output is long enough
        'stmts = [{0}, "putStrLn . concat . replicate 100000 $ \\" \\""]'.format(', '.join('"{0}"'.format(e.replace('\\', '\\\\').replace('"', '\\"')) for e in (lines + [arg['code']]))),
        'run stmt',
        '    | stmt `looks_like` "import "',
        '    = do ctx <- getContext',
        '         mod <- parseImportDecl stmt',
        '         setContext $ (IIDecl mod) : ctx',
        '    | any (stmt `looks_like`) prefixes = do runDecls stmt; return ()',
        #'    | otherwise = do execStmt stmt execOptions; return ()',
        '    | otherwise = do runStmt stmt SingleStep; return ()',
        '    where s `looks_like` p = p `isPrefixOf` dropWhile isSpace s',
        '          prefixes = [ "class ", "instance ", "data ", "newtype ", "type ", "default ", "default("]',
        #'main = runGhc (Just "/opt/ghc/8.0.1/lib/ghc-8.0.0.20160127/") $ do',
        'main = runGhc (Just "/usr/lib/ghc") $ do',
        '    dflags <- getSessionDynFlags',
        '    setSessionDynFlags dflags',
        '    ctx <- getContext',
        '    setContext $ (IIDecl . simpleImportDecl $ mkModuleName "Prelude") : ctx',
        '    mapM run stmts',
    ]
    #print(repr(line))

    return (yield from rextester(arg, line, send))


#@asyncio.coroutine
#def ghci(arg, lines, send):
#    print('ghci')
#
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
#    r = yield from fetch('POST', url, data=data, headers=headers, content='raw')
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


@asyncio.coroutine
def rustmain(arg, lines, send):
    print('rustmain')

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
        '#![allow(bad_style, unused)]',
        '#![feature(non_ascii_idents, stmt_expr_attributes)]',
        'fn main() {',
        '    println!("{:?}", {',
        code,
        '    });',
        '}',
    ]

    return (yield from rust(arg, line, send))


@asyncio.coroutine
def rusti32main(arg, lines, send):
    print('rusti32main')

    arg.update({
        'raw': None,
        'version': 'nightly',
    })
    code = '\n'.join(lines) or arg['code'] or ''
    line = [
        '#![allow(bad_style, unused)]',
        '#![feature(non_ascii_idents, stmt_expr_attributes)]',
        'fn main() {',
        '    println!("{:?}", {',
        code,
        '    });',
        '}',
    ]

    return (yield from rusti32(arg, line, send))


@asyncio.coroutine
def geordi(arg, lines, send):

    arg.update({
        'lang': 'c++(gcc)',
        'args': arg['args'] or '-std=c++1z',
        'raw': None,
    })
 
    line = [
        '#include <bits/stdc++.h>',
        '#include <cxxabi.h>',
        'using namespace std;',
        # comma in ostream
        'template <typename Ch, typename Tr, typename T> std::basic_ostream<Ch, Tr> &operator,(std::basic_ostream<Ch, Tr> & o, T const & t) { return o << ", " << t; }',
        'template <typename Ch, typename Tr> std::basic_ostream<Ch, Tr> &operator,(std::basic_ostream<Ch, Tr> & o, std::basic_ostream<Ch, Tr> & (* const f) (std::basic_ostream<Ch, Tr> &)) { return o << f; }',
        # bark
        '#define BARK (::std::printf(" %s ", __PRETTY_FUNCTION__), ::std::fflush(stdout))',
        # type
        'namespace type_strings_detail {',
        'template <typename T> std::string type_string() { std::string s = std::type_index(typeid(T)).name(); int status = -1; return abi::__cxa_demangle(s.c_str(), 0, 0, &status); }',
        'template <typename> struct type_tag {};',
        #'template <typename Ch, typename Tr, typename T> std::basic_ostream<Ch, Tr> &operator<<(std::basic_ostream<Ch, Tr> & o, type_tag<T>()) { return o << type_string<T>(); }',
        #'template <typename Ch, typename Tr, typename T> std::basic_ostream<Ch, Tr> &operator<<(std::basic_ostream<Ch, Tr> & o, type_tag<const T>()) { return o << type_string<T>() << " const"; }',
        #'template <typename Ch, typename Tr, typename T> std::basic_ostream<Ch, Tr> &operator<<(std::basic_ostream<Ch, Tr> & o, type_tag<volatile T>()) { return o << type_string<T>() << " volatile"; }',
        #'template <typename Ch, typename Tr, typename T> std::basic_ostream<Ch, Tr> &operator<<(std::basic_ostream<Ch, Tr> & o, type_tag<const volatile T>()) { return o << type_string<T>() << " const volatile"; }',
        'struct adl_hint {};',
        'template <typename Ch, typename Tr, typename T> std::basic_ostream<Ch, Tr> &operator<<(std::basic_ostream<Ch, Tr> & o, adl_hint(type_tag<T>)) { return o << type_string<T>(); }',
        'template <typename Ch, typename Tr, typename T> std::basic_ostream<Ch, Tr> &operator<<(std::basic_ostream<Ch, Tr> & o, adl_hint(type_tag<const T>)) { return o << type_string<T>() << " const"; }',
        'template <typename Ch, typename Tr, typename T> std::basic_ostream<Ch, Tr> &operator<<(std::basic_ostream<Ch, Tr> & o, adl_hint(type_tag<volatile T>)) { return o << type_string<T>() << " volatile"; }',
        'template <typename Ch, typename Tr, typename T> std::basic_ostream<Ch, Tr> &operator<<(std::basic_ostream<Ch, Tr> & o, adl_hint(type_tag<const volatile T>)) { return o << type_string<T>() << " const volatile"; }',
        '}',
        #'template <typename T> type_strings_detail::type_tag<T> TYPE() { return type_strings_detail::type_tag<T>(); }',
        'template <typename T> type_strings_detail::adl_hint TYPE(type_strings_detail::type_tag<T>) { return type_strings_detail::adl_hint(); }',
    ]
    # not correct but maybe enough?
    if '++14' in arg['args'] or '++1y' in arg['args']:
        line = [
            # experimental
            '#include <experimental/string_view>',
            '#include <experimental/optional>',
        ] + line

    printing = re.compile(r'<<(?P<print>.+?)(?:;(?P<code>.*))?')
    statement = re.compile(r'{{(?P<main>.+?)}}(?P<code>.*)?')

    p = printing.fullmatch(arg['code'])
    if p:
        p = p.groupdict()
        line.extend([
            p['code'] or '',
            'int main() {{ std::cout << {}; std::cout << std::endl; return 0; }}'.format(p['print']),
        ])
        print(line)
        return (yield from rextester(arg, line, send))

    s = statement.fullmatch(arg['code'])
    if s:
        s = s.groupdict()
        line.extend([
            s['code'] or '',
            'int main() {{ {} }}'.format(s['main']),
        ])
        print(line)
        return (yield from rextester(arg, line, send))

    line.append(arg['code'])
    print(line)

    return (yield from rextester(arg, line, send))

help = [
    ('vimcn'        , 'vimcn (code)'),
    ('bpaste'       , 'bpaste[:lang] (code)'),
    ('rust'         , 'rust (code)'),
    ('go'           , 'go (code)'),
    ('codepad'      , 'codepad:<lang> [run] (code)'),
    ('rex'          , 'rex:<lang> [args --] (code)'),
]

func = [
    (vimcn          , r"vimcn(?:\s+(?P<code>.+))?"),
    (bpaste         , r"bpaste(?::(?P<lang>\S+))?(?:\s+(?P<code>.+))?"),
    (rust           , r"rust(?::(?P<version>stable|beta|nightly))?(?::(?P<raw>raw))?(?:\s+(?P<code>.+))?"),
    (rusti32        , r"rusti32(?::(?P<version>stable|beta|nightly))?(?::(?P<raw>raw))?(?:\s+(?P<code>.+))?"),
    (go             , r"go(?::(?P<raw>raw))?(?:\s+(?P<code>.+))?"),
    (codepad        , r"codepad:(?P<lang>\S+)(?:\s+(?P<run>run)(?::(?P<raw>raw))?)?(?:\s+(?P<code>.+))?"),
    (hackerearth    , r"hack:(?P<lang>[^\s:]+)(?::(?P<raw>raw))?(?:\s+(?P<code>.+))?"),
    (rextester      , r"rex:(?P<lang>[^\s:]+)(?::(?P<raw>raw))?(?:\s+(?P<args>.+?)\s+--)?(?:\s+(?P<code>.+))?"),
    (hylang         , r"hy(?:\s+(?P<code>.+))?"),
    (python3        , r">> (?P<code>.+)"),
    (python3        , r"py (?P<code>.+)"),
    (haskell        , r"\\\\ (?P<code>.+)"),
    (rustmain       , r"rs (?P<code>.+)"),
    (rusti32main    , r"rsi32 (?P<code>.+)"),
    (geordi         , r"geordi(?:\s+(?P<args>.+?)\s+--)?(?:\s+(?P<code>.+))?"),
]
