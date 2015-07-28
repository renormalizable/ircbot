import re


class dePrefix:

    def __init__(self):
        #self.r = re.compile(r'(?:(\[)?(?P<nick>.+?)(?(1)\]|:) )?(?P<message>.*)')
        #self.r = re.compile(r'(\[(?P<nick>.+?)\] )?((?P<to>[^\s\']+?): )?(?P<message>.*)')
        #self.r = re.compile(r'(\[(?P<nick>.+?)\] )?((?P<to>[^\'"]+?)[:,] )?(?P<message>.*)')
        self.r = re.compile(r'((?:(?P<s>\[)|(?P<r>\())(?P<nick>.+?)(?(s)\])(?(r)\)) )?((?P<to>[^\'"]+?)[:,] )?(?P<message>.*)')

    def __call__(self, n, m):
        r = self.r.fullmatch(m).groupdict()
        #return (r['to'].strip() if r['to'] else r['nick'].strip() if r['nick'] else n, r['message'])
        return (r['to'] or r['nick'] or n, r['message'])


class Normalize:

    def __init__(self):
        self.alias = str.maketrans({
            '　': '  ',
            '，': ', ',
            '。': '. ',
            '！': '! ',
            '？': '? ',
            '：': ': ',
            '；': '; ',
            '（': ' (',
            '）': ') ',
        })
        self.esc = [
            # irssi
            (r'\x02', '\x02'),
            (r'\x03', '\x03'),
            (r'\x04', '\x04'),
            (r'\x06', '\x06'),
            (r'\x07', '\x07'),
            (r'\x0f', '\x0f'),
            (r'\x16', '\x16'),
            (r'\x1b', '\x1b'),
            (r'\x1d', '\x1d'),
            (r'\x1f', '\x1f'),
        ]
        self.colorreg = re.compile(r'(\\x03\d{1,2}(,\d{1,2})?)')

    def __call__(self, message, *, stripspace=True, stripline=True, newline=True, convert=True, escape=True):
        #lines = str(message).splitlines() if stripline else [str(message)]
        l = str(message).translate(self.alias) if convert else str(message)
        lines = l.splitlines() if stripline else [l]
        if stripspace:
            lines = map(lambda l: ' '.join(l.split()), lines)
        if stripline:
            lines = filter(lambda l: l, lines)
        line = '\\x0304\\n\\x0f '.join(lines) if newline else ' '.join(lines)
        #if convert:
        #    line = line.translate(self.alias)
        if escape:
            for (s, e) in self.esc:
                line = line.replace(s, e)
        else:
            line = self.colorreg.sub('', line)
            for (s, e) in self.esc:
                line = line.replace(s, '')
        return line
