import re
import importlib

import bottom


class dePrefix:
    def __init__(self):
        #self.r = re.compile(r'(?:(\[)?(?P<nick>.+?)(?(1)\]|:) )?(?P<message>.*)')
        #self.r = re.compile(r'(\[(?P<nick>.+?)\] )?((?P<to>[^\s\']+?): )?(?P<message>.*)')
        self.r = re.compile(r'(\[(?P<nick>.+?)\] )?((?P<to>[^\'"]+?): )?(?P<message>.*)')
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
        return line

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
        self.normalize = Normalize()
        self.modules = importlib.import_module('modules')

    def reload(self):
        self.modules = importlib.reload(self.modules)

    def addlines(self, nick, l):
        if nick not in self.lines:
            self.lines[nick] = [l, self.loop.call_later(self.time, lambda: self.lines.pop(nick, None))]
        else:
            self.lines[nick][0].extend(l)
        #item = self.lines.get(nick, None)
        #if item:
        #    item[0].extend(l)
        #else:
        #    self.lines[nick] = [l, self.loop.call_later(self.time, lambda: self.lines.pop(nick, None))]

    def getlines(self, nick):
        item = self.lines.pop(nick, None)
        if item:
            item[1].cancel()
            return item[0]
        else:
            return []

    def sendm(self, target, message, *, command='PRIVMSG', to='', raw=False, mlimit=0, color=None, **kw):
        prefix = (to + ': ') if to else ''
        message = ('' if raw else prefix) + self.normalize(message, **kw)
        print(message)
        for (i, m) in enumerate(splitmessage(message.encode('utf-8'), self.msglimit)):
            if mlimit > 0 and i >= mlimit:
                self.send(command, target=target, message=prefix + '太多了啦...')
                break
            self.send(command, target=target, message=m.decode('utf-8'))

    #def sendl(self, target, line, n, *, llimit=0, loffset=0, **kw):
    #    sent = False

    #    if loffset > 0:
    #        pass

    #    for (i, m) in enumerate(line):
    #        if n > 0 and i >= n:
    #            break
    #        if llimit > 0 and i >= llimit:
    #            #d = {k: kw[k] for k in ['command', 'to'] if k in kw}
    #            #self.sendm(target, '太长了啦...', **d)
    #            command = kw.get('command', 'PRIVMSG')
    #            to = kw.get('to', '')
    #            prefix = (to + ': ') if to else ''
    #            self.send(command, target=target, message=prefix + '太长了啦...')
    #            break
    #        self.sendm(target, m, **kw)
    #        sent = True
    #    if not sent:
    #        raise Exception()

    #def sender(self, target, content, *, n=-1, llimit=-1, loffest=-1, **kw):
    #    if n < 0:
    #        self.sendm(target, content, **kw)
    #    else:
    #        d = {}
    #        if llimit >= 0:
    #            d['llimit'] = llimit
    #        if loffset >=0:
    #            d['loffset'] = loffset
    #        self.sendl(target, content, n, **d, **kw)
    #        #if llimit < 0:
    #        #    self.sendl(target, content, n, **kw)
    #        #else:
    #        #    self.sendl(target, content, n, llimit=llimit, **kw)

    def sendl(self, target, line, n, *, llimit=0, **kw):
        sent = False
        for (i, m) in enumerate(line):
            if llimit > 0 and i >= llimit:
                #d = {k: kw[k] for k in ['command', 'to'] if k in kw}
                #self.sendm(target, '太长了啦...', **d)
                command = kw.get('command', 'PRIVMSG')
                to = kw.get('to', '')
                prefix = (to + ': ') if to else ''
                self.send(command, target=target, message=prefix + '太长了啦...')
                break
            self.sendm(target, m, **kw)
            sent = True
            if n > 0 and i >= (n - 1):
                break
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
