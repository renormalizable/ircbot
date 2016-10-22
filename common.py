import re


class dePrefix:

    def __init__(self):
        #self.r = re.compile(r'(?:(\[)?(?P<nick>.+?)(?(1)\]|:) )?(?P<message>.*)')
        #self.r = re.compile(r'(\[(?P<nick>.+?)\] )?((?P<to>[^\s\']+?): )?(?P<message>.*)')
        #self.r = re.compile(r'(\[(?P<nick>.+?)\] )?((?P<to>[^\'"]+?)[:,] )?(?P<message>.*)')
        self.r = re.compile(r'((?:(?P<s>\[)|(?P<r>\())(?P<nick>.+?)(?(s)\])(?(r)\)) )?((?P<to>[^\'"]+?)[:,] )?(?P<message>.*)', re.DOTALL)
        self.esc = re.compile(r'(\x03\d{1,2}(,\d{1,2})?|\x02|\x03|\x04|\x06|\x07|\x0f|\x16|\x1b|\x1d|\x1f)')
        self.orz = re.compile(r'((?:(?P<s>\[))(?P<nick>[\x00-\x1f].+?[\x00-\x1f])(?(s)\]) )?((?P<to>[^\'"]+?)[:,] )?(?P<message>.*)', re.DOTALL)

    def __call__(self, n, m):
        # orizon
        r = self.orz.fullmatch(m).groupdict()
        if r['nick']:
            r['nick'] = self.esc.sub('', r['nick'])
        else:
            r = self.r.fullmatch(self.esc.sub('', m)).groupdict()
        #return (r['to'].strip() if r['to'] else r['nick'].strip() if r['nick'] else n, r['message'])
        return (r['to'] or r['nick'] or n, r['message'])


class Normalize:

    def __init__(self, stripspace=True, stripline=True, newline='\\x0304\\n\\x0f ', convert=True, escape=True):
        self.stripspace = stripspace
        self.stripline = stripline
        self.newline = newline
        self.convert = convert
        self.escape = escape

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
            # https://github.com/irssi/irssi/blob/master/src/fe-common/core/formats.c#L1086
            # IS_COLOR_CODE(...)
            # https://github.com/irssi/irssi/blob/master/src/fe-common/core/formats.c#L1254
            # format_send_to_gui(...)
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

    def __call__(self, message, *, stripspace=None, stripline=None, newline=None, convert=None, escape=None):
        if stripspace == None: stripspace = self.stripspace
        if stripline == None: stripline = self.stripline
        if newline == None: newline = self.newline
        if convert == None: convert = self.convert
        if escape == None: escape = self.escape

        #lines = str(message).splitlines() if stripline else [str(message)]
        l = str(message).translate(self.alias) if convert else str(message)
        lines = l.splitlines() if stripline else [l]
        if stripspace:
            lines = map(lambda l: ' '.join(l.split()), lines)
        if stripline:
            lines = filter(lambda l: l, lines)
        line = newline.join(lines)
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


def splitmessage(s, n):
    # rules
    starting = ''
    ending = ''

    # zh
    starting += '、。〃〆〕〗〞﹚﹜！＂％＇），．：；？！］｝～'
    ending += '〈《「『【〔〖〝﹙﹛＄（．［｛￡￥'

    # ja
    starting += '｝〕〉》」』】〙〗〟｠' + 'ヽヾーァィゥェォッャュョヮヵヶぁぃぅぇぉっゃゅょゎゕゖㇰㇱㇲㇳㇴㇵㇶㇷㇸㇹㇺㇻㇼㇽㇾㇿ々〻' + '゠〜・、。'
    ending += '｛〔〈《「『【〘〖〝｟'

    if n < 4:
        return

    bs = s.encode('utf-8')

    # need splitting
    # n should large enough for a single character
    while len(bs) > n:
        i = n + 1

        # find good ending with one extra character
        while 0 <= i and (bs[i] & 0xc0) == 0x80:
            i = i + 1

        # result candidate
        str = bs[:i].decode('utf-8')

        j = len(str) - 1

        print('j = {}'.format(j))

        # check first character in next line and last character in this line
        while (0 <= j and str[j] in starting) or (1 <= j and str[j - 1] in ending):
            j = j - 1

        # if too short
        if j <= 0:
            return

        ## if cannot find good line
        #if j <= 0:
        #    j = len(str) - 1

        str = str[:j]

        yield str

        bs = bs[len(str.encode('utf-8')):]

    yield bs.decode('utf-8')
