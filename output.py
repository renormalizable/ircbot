

alias = {
    '　': '  ',
    '，': ', ',
    '。': '. ',
    '！': '! ',
    '？': '? ',
    '：': ': ',
}
alias = str.maketrans(alias)
esc = [
    ('\\x0f', '\x0f'),
    ('\\x03', '\x03'),
    ('\\x02', '\x02'),
    ('\\x1d', '\x1d'),
    ('\\x1f', '\x1f'),
]

def normalize(message, stripspace=True, stripline=True, newline=True, convert=True, escape=True):
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
        line = line.translate(alias)
    if escape:
        for (s, e) in esc:
            line = line.replace(s, e)
    return line

def ircescape(t):
    table = [
        ('\\x0f', '\x0f'),
        ('\\x03', '\x03'),
        ('\\x02', '\x02'),
        ('\\x1d', '\x1d'),
        ('\\x1f', '\x1f'),
    ]
    for (s, e) in table:
        t = t.replace(s, e)
    return t

def splitmessage(s, n):
    while len(s) > n:
        i = n
        while (s[i] & 0xc0) == 0x80:
            i = i - 1
        print(i)
        yield s[:i]
        s = s[i:]
    yield s

def send(bot, command, *, target='', message='', to='', toall=False, llimit=0, color=None, **kw):
    # (512 - 2) / 3 = 170
    # 430 bytes should be safe
    limit = 430

    prefix = (to + ': ') if to else ''

    #message = normalize(message, **kw)
    message = ('' if toall else prefix) + normalize(message, **kw)
    print(message)
    for (i, m) in enumerate(splitmessage(message.encode('utf-8'), limit)):
        if llimit and i >= llimit:
            bot.send(command, target=target, message=prefix + '太多了啦...')
            break
        bot.send(command, target=target, message=m.decode('utf-8'))

def sendl(l, n, send, *, olimit=0, **kw):
    i = 0
    for e in l:
        if i < n and (olimit == 0 or i < olimit):
            send(e, **kw)
            i = i + 1
        else:
            break
    if i == 0:
        raise Exception()
    if i == olimit and n > olimit:
        send('太长了啦...')
