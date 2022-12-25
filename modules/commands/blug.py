from datetime import datetime, timezone, timedelta

from .tool    import xml


async def event(arg, send):
    n = int(arg['n'] or '1')
    arg.update({
        'n': str(n * 2 if arg['detail'] else n),
        'url': 'https://beijinglug.club/?plugin=all-in-one-event-calendar&controller=ai1ec_exporter_controller&action=export_events&xml=true',
        'xpath': '//vevent',
    })
    def format(self, es):
        def parsedate(s):
            try:
                return datetime.strptime(s, '%Y%m%dT%H%M%S')
            except:
                return datetime.strptime(s, '%Y%m%d')
        def future(e):
            t = parsedate(e.xpath('./dtstart')[0].xpath('string()'))
            t = t.replace(tzinfo=timezone(timedelta(hours=8)))
            # being late by one hour is ok
            return datetime.now(timezone(timedelta(hours=8))) < t + timedelta(hours=1)
        def key(e):
            return parsedate(e.xpath('./dtstart')[0].xpath('string()'))
        def formatter(time, summary, description, location, coordinate, url):
            if arg['detail']:
                return [
                    '\\x02{0:%Y %b %d %a %H:%M}\\x0f {1} @ {2} [\\x0302 {3} \\x0f]'.format(
                        time,
                        summary,
                        '{} ({})'.format(location, coordinate) if coordinate else location,
                        url),
                    description,
                ]
            else:
                return [
                    '\\x02{0:%b %d %a %H:%M}\\x0f {1} @ {2} [\\x0302 {3} \\x0f]'.format(time, summary, location.split(' @ ')[0], url),
                ]
        field = [
            ('./dtstart', 'text', lambda x: parsedate(self.iter_first(x))),
            ('./summary', 'text', lambda x: self.iter_first(x).strip()),
            ('./description', 'text', lambda x: ' '.join(self.iter_first(x).strip().split())),
            ('./location', 'text', lambda x: self.iter_first(x).strip()),
            ('./geo', 'text', self.iter_first),
            ('./url/@uri', '', self.iter_first),
        ]

        # workaround for dtstart format
        new = [e for e in es[1:] if future(e)]
        if not new:
            raise Exception('we need more parties \o/')
        return (formatter(*self.get_fields(self.get, e, field)) for e in sorted(new, key=key))

    return (await xml(arg, [], send, format_new=format))


help = [
    ('blug'         , 'blug <command> (command is one of the following: event; see \'help blug-<command> for detail)'),
    ('blug-event'   , 'blug event [detail] [#max number][+offset]'),
]

func = [
    (event          , r"blug\s+event(?:\s+(?P<detail>detail))?(\s+(#(?P<n>\d+))?(\+(?P<offset>\d+))?)?"),
]
