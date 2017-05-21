import asyncio
from urllib.parse  import quote_plus
from datetime import datetime, timezone, timedelta

from .common import Get
from .tool import html, xml, addstyle, htmlparse
#from .tool import fetch, htmltostr, html, xml, addstyle, jsonparse, htmlparse


@asyncio.coroutine
def event(arg, send):
    print('blug event')

    arg.update({
        'n': arg['n'] or '1',
        'url': 'https://beijinglug.club/?plugin=all-in-one-event-calendar&controller=ai1ec_exporter_controller&action=export_events&xml=true',
        'xpath': '//vevent',
    })
    field = [
        ('./dtstart', 'text', '{}'),
        ('./summary', 'text', '{}'),
        ('./description', 'text', '{}'),
        ('./location', 'text', '{}'),
        ('./geo', 'text', '{}'),
        ('./url', 'uri', '{}'),
    ]
    def parsedate(s):
        try:
            return datetime.strptime(s, '%Y%m%dT%H%M%S')
        except:
            return datetime.strptime(s, '%Y%m%d')
    def transform(l):
        def future(e):
            t = parsedate(e.xpath('./dtstart')[0].xpath('string()'))
            t = t.replace(tzinfo=timezone(timedelta(hours=8)))
            return datetime.now(timezone(timedelta(hours=8))) < t
        def key(e):
            return parsedate(e.xpath('./dtstart')[0].xpath('string()'))
        # workaround for dtstart format
        new = list(filter(future, l[1:]))
        if new:
            return sorted(new, key=key)
        else:
            raise Exception('we need more parties \o/')
    def format(l):
        def formatter(e):
            t = parsedate(e[0])
            sum = e[1].strip()
            des = ' '.join(e[2].strip().split())
            loc = e[3].strip()
            geo = e[4]
            url = e[5]
            if arg['detail']:
                if geo:
                   loc = '{} ({})'.format(loc, geo)
                return '\\x02{0:%Y %b %d %a %H:%M}\\x0f {1} @ {2} : {3} [\\x0302 {4} \\x0f]'.format(t, sum, loc, des, url)
            else:
                loc = loc.split(' @ ')[0]
                return '\\x02{0:%b %d %a %H:%M}\\x0f {1} @ {2} [\\x0302 {3} \\x0f]'.format(t, sum, loc, url)
        return map(formatter, l)

    return (yield from xml(arg, [], send, field=field, transform=transform, format=format))


help = [
    ('blug'         , 'blug <command> (command is one of the following: event; see \'help blug-<command> for detail)'),
    ('blug-event'   , 'blug event [detail] [#max number][+offset]'),
]

func = [
    (event          , r"blug\s+event(?:\s+(?P<detail>detail))?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
]
