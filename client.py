import re
import importlib

import bottom


class dePrefix:
    def __init__(self):
        #self.r = re.compile(r'(?:(\[)?(?P<nick>.+?)(?(1)\]|:) )?(?P<message>.*)')
        self.r = re.compile(r'(\[(?P<nick>.+?)\] )?((?P<to>[^\s\']+?): )?(?P<message>.*)')
    def __call__(self, n, m):
        r = self.r.fullmatch(m).groupdict()
        #return (r['nick'].strip() if r['nick'] else n, r['message'])
        return (r['to'].strip() if r['to'] else r['nick'].strip() if r['nick'] else n, r['message'])

class Normalize:
    def __init__(self):
        self.alias = str.maketrans({
            '　': '  ',
            '，': ', ',
            '。': '. ',
            '！': '! ',
            '？': '? ',
            '：': ': ',
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
    def __call__(self, message, *, stripspace=True, stripline=True, newline=True, convert=True, escape=True):
        lines = str(message).splitlines() if stripline else [message]
        if stripspace:
            lines = map(lambda l: ' '.join(l.split()), lines)
        if stripline:
            lines = filter(lambda l: l, lines)
        line = '\\x0304\\n\\x0f '.join(lines) if newline else ' '.join(lines)
        if convert:
            line = line.translate(self.alias)
        if escape:
            for (s, e) in self.esc:
                line = line.replace(s, e)
        return line

normalize = Normalize()

def splitmessage(s, n):
    while len(s) > n:
        i = n
        while (s[i] & 0xc0) == 0x80:
            i = i - 1
        print(i)
        yield s[:i]
        s = s[i:]
    yield s

class Client(bottom.Client):
    def __init__(self, loop, host, port, **kw):
        super().__init__(host, port, **kw)
        self.loop = loop
        self.lines = {}
        self.time = 60
        # (512 - 2) / 3 = 170
        # 430 bytes should be safe
        self.msglimit = 430

        self.deprefix = dePrefix()
        self.modules = importlib.import_module('modules')

    def reload(self):
        self.modules = importlib.reload(self.modules)

    def addlines(self, nick, l):
        if nick not in self.lines:
            self.lines[nick] = [l, self.loop.call_later(self.time, lambda: self.lines.pop(nick, None))]
        else:
            self.lines[nick][0] += l

    def getlines(self, nick):
        item = self.lines.pop(nick, None)
        if item:
            item[1].cancel()
            return item[0]
        else:
            return ''

    def sendm(self, target, message, *, command='PRIVMSG', to='', raw=False, mlimit=0, color=None, **kw):
        prefix = (to + ': ') if to else ''
        message = ('' if raw else prefix) + normalize(message, **kw)
        print(message)
        for (i, m) in enumerate(splitmessage(message.encode('utf-8'), self.msglimit)):
            if mlimit and i >= mlimit:
                self.send(command, target=target, message=prefix + '太多了啦...')
                break
            self.send(command, target=target, message=m.decode('utf-8'))

    def sendl(self, target, line, n, *, llimit=0, **kw):
        sent = False
        for (i, m) in enumerate(line):
            if i >= n:
                break
            if llimit and i >= llimit:
                self.sendm(target, '太长了啦...', **kw)
                break
            self.sendm(target, m, **kw)
            sent = True
        if not sent:
            raise Exception()

    def sender(self, target, content, *, n=-1, llimit=-1, **kw):
        if n < 0:
            self.sendm(target, content, **kw)
        else:
            if llimit < 0:
                self.sendl(target, content, n, **kw)
            else:
                self.sendl(target, content, n, llimit=llimit, **kw)

