import bottom

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
            (r'\x0f', '\x0f'),
            (r'\x03', '\x03'),
            (r'\x02', '\x02'),
            (r'\x1d', '\x1d'),
            (r'\x1f', '\x1f'),
        ]
    def __call__(self, message, *, stripspace=True, stripline=True, newline=True, convert=True, escape=True):
        line = str(message).splitlines() if stripline else [message]
        if stripspace:
            line = map(lambda l: ' '.join(l.split()), line)
        if stripline:
            line = filter(lambda l: l, line)
        if newline:
            line = '\\x0304\\n\\x0f '.join(line)
        else:
            line = ' '.join(line)
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

    def sender(self, target, content, *, n=-1, **kw):
        if n < 0:
            self.sendm(target, content, **kw)
        else:
            self.sendl(target, content, n, **kw)

#def sendl(l, n, send, *, olimit=0, **kw):
#    i = 0
#    for e in l:
#        if i < n and (olimit == 0 or i < olimit):
#            send(e, **kw)
#            i = i + 1
#        else:
#            break
#    if i == 0:
#        raise Exception()
#    if i == olimit and n > olimit:
#        send('太长了啦...')
