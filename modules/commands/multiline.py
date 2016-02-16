import asyncio
import re
import json
from urllib.parse import urlsplit

from .common import Get
from .tool import fetch, html, regex


@asyncio.coroutine
def getcode(url):
    site = {
        # raw
        'cfp.vim-cn.com':              '.',
        'p.vim-cn.com':                '.',
        'ix.io':                       '.',
        'sprunge.us':                  '.',
        # parse
        'paste.ubuntu.com':            '//*[@id="contentColumn"]/div/div/div/table/tbody/tr/td[2]/div/pre',
        'pastebin.ubuntu.com':         '//*[@id="contentColumn"]/div/div/div/table/tbody/tr/td[2]/div/pre',
        'paste.kde.org':               '//*[@id="show"]/div[1]/div/div[2]/div',
        'paste.opensuse.org':          '//*[@id="content"]/div[2]/div[2]/div',
        'paste.fedoraproject.org':     '//*[@id="paste_form"]/div[1]/div/div[3]',
        'codepad.org':                 '/html/body/div/table/tbody/tr/td/div[1]/table/tbody/tr/td[2]/div/pre',
        'www.fpaste.org':              '//*[@id="paste_form"]/div[1]/div/div[3]',
        'bpaste.net':                  '//*[@id="paste"]/div/table/tbody/tr/td[2]/div',
        'pastebin.com':                '//*[@id="paste_code"]',
        #'pastebin.com':                '//*[@id="selectable"]/div',
        'code.bulix.org':              '//*[@id="contents"]/pre',
        'dpaste.com':                  '//*[@id="content"]/table/tbody/tr/td[2]/div/pre',
        'ideone.com':                  '//*[@id="source"]/pre/ol/li/div',
        'gist.github.com':             '//*[@class="file"]/div[2]/table/tbody/tr/td[contains(@class, "blob-code")]',
        'lpaste.net':                  '//*[@id="paste"]/div/div[3]/table/tbody/tr/td[2]/pre',
        'paste.xinu.at':               '//*[@id="wrap"]/div[3]/div[2]/div/pre/div/span',
        #'notepad.cc':                  '//*[@id="contents"]',
        'www.refheap.com':             '//*[@id="paste"]/table/tbody/tr/td[2]/div/pre',
        'paste.pound-python.org':      '//*[@id="paste"]/div/ol/li/span',
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
def geturl(msg):
    #reg = re.compile(r"(?P<method>GET|POST)\s+(?P<url>http\S+)(?:\s+(?P<params>\{.+?\}))?(?:\s+:(?P<content>\w+))?", re.IGNORECASE)
    reg = re.compile(r"(?P<method>GET|POST)\s+(?P<url>http\S+)(?:\s+p(?P<params>\{.+?\}))?(?:\s+h(?P<headers>\{.+?\}))?(?:\s+:(?P<content>\w+))?", re.IGNORECASE)
    arg = reg.fullmatch(msg)
    if arg:
        d = arg.groupdict()
        print(d)
        params = json.loads(d.get('params') or '{}')
        headers = json.loads(d.get('headers') or '{}')
        content = d.get('content')
        if content:
            r = yield from fetch(d['method'], d['url'], params=params, headers=headers, content='raw')
            #text = str(getattr(r, content.lower()) or '')
            text = str(getattr(r, content))
        else:
            text = yield from fetch(d['method'], d['url'], params=params, headers=headers, content='text')
    else:
        raise Exception()

    return [text]


@asyncio.coroutine
def fetcher(msg):
    try:
        return (yield from getcode(msg))
    except:
        print('not paste bin')
        return (yield from geturl(msg))

# util


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

help = [
    ('clear'        , 'clear'),
    ('undo'         , 'undo [number]'),
]

func = [
    (clear          , r"clear"),
    (undo           , r"undo(?:\s+(?P<n>\d+))?"),
]
