import asyncio
import time


@asyncio.coroutine
def echo(arg, send):
    #send(arg[0])
    send(arg['content'], raw=True)

@asyncio.coroutine
def ping(arg, send):
    send("ping!")
    #send("\\x0305ping!\\x0f")

@asyncio.coroutine
def pong(arg, send):
    send("pong!")

class ping2c():
    def __init__(self):
        self.i = 3
        self.tt = time.time()

    @asyncio.coroutine
    def __call__(self, arg, send):
       print(self.i)
       t = time.time()
       if t - self.tt > 20:
          self.tt = t
          self.i = 3
       elif self.i <= 0:
          send('好累啊...')
       if self.i == 1:
          send("\\x0304ping!!!!!!!!!\\x0f")
          self.i = self.i - 1
       elif self.i > 0:
          send("\\x0304ping!\\x0f")
          self.i = self.i - 1

ping2 = ping2c()

@asyncio.coroutine
def pia(arg, send):
    content = arg['content'] or ''

    if 'varia' not in content:
        send('(╯°Д°)╯ ┻━┻ ' + content)
    else:
        send('(╯°Д°)╯ ┻━┻ ' + '不要 pia 我!')

@asyncio.coroutine
def mua(arg, send):
    content = arg['content'] or ''

    if 'varia' not in content:
        send('o(*￣3￣)o ' + content)
    else:
        send('o(*￣3￣)o ' + '谢谢啦~')

@asyncio.coroutine
def color(arg, send):
    c = [
        ('00', 'white'),
        ('01', 'black'),
        ('02', 'blue'),
        ('03', 'green'),
        ('04', 'red'),
        ('05', 'brown'),
        ('06', 'purple'),
        ('07', 'orange'),
        ('08', 'yellow'),
        ('09', 'light green'),
        ('10', 'teal'),
        ('11', 'light cyan'),
        ('12', 'light blue'),
        ('13', 'pink'),
        ('14', 'grey'),
        ('15', 'light grey'),
    ]
    send('\\x02bold\\x02 \\x1ditalic\\x1d \\x1funderline\\x1f')
    send(' '.join(map(lambda x: '\\x03{0}{0} {1}\\x0f'.format(*x), c[:8])))
    send(' '.join(map(lambda x: '\\x03{0}{0} {1}\\x0f'.format(*x), c[8:])))

@asyncio.coroutine
def mode(arg, send):
    u = [
        ('D', 'deaf'),
        ('g', 'caller-id'),
        ('i', 'invisible'),
        ('Q', 'no forwarding'),
        ('R', 'block unidentified'),
        ('w', 'see wallops'),
        ('Z', 'connected via SSL'),
    ]
    c = [
        ('b', 'channel ban'),
        ('c', 'color filter'),
        ('C', 'block CTCPS'),
        ('e', 'ban exemption'),
        ('f', 'forward on uninvited'),
        ('F', 'enable forwarding'),
        ('g', 'allow anybody to invite'),
        ('i', 'invite-only'),
        ('I', 'invite-only exemption'),
        ('j', 'join throttling'),
        ('k', 'channel password'),
        ('l', 'join limit'),
        ('L', 'large ban/exempt/invex lists'),
        ('m', 'moderated'),
        ('n', 'prevent external send'),
        ('p', 'paranoid'),
        ('P', 'permanent channel'),
        ('q', 'quiet user'),
        ('Q', 'block forwarded users'),
        ('r', 'block unidentified'),
        ('s', 'secret channel'),
        ('S', 'SSL-only'),
        ('t', 'only ops can change topic'),
        ('z', 'reduced moderation'),
    ]
    print(len(c))
    send('\\x0304user\\x0f ' + ' '.join(map(lambda e: '\\x0300{0}\\x0f({1})'.format(*e), u)))
    send('\\x0304channel\\x0f ' + ' '.join(map(lambda e: '\\x0300{0}\\x0f({1})'.format(*e), c[:12])))
    send('\\x0304cont.\\x0f ' + ' '.join(map(lambda e: '\\x0300{0}\\x0f({1})'.format(*e), c[12:])))
    send('see [\\x0302https://freenode.net/using_the_network.shtml\\x0f] for more infomation')


@asyncio.coroutine
def latex(arg, send):
    symbol = [
        (r'\alpha',       '\U0001d6fc'),
        (r'\pi',          '\U0001d6d1'),
        (r'\Alpha',       '\u0391'),
        (r'\Beta',        '\u0392'),
        (r'\Gamma',       '\u0393'),
        (r'\Delta',       '\u0394'),
        (r'\Epsilon',     '\u0395'),
        (r'\Zeta',        '\u0396'),
        (r'\Eta',         '\u0397'),
        (r'\Theta',       '\u0398'),
        (r'\Iota',        '\u0399'),
        (r'\Kappa',       '\u039a'),
        (r'\Lambda',      '\u039b'),
        (r'\Mu',          '\u039c'),
        (r'\Nu',          '\u039d'),
        (r'\Xi',          '\u039e'),
        (r'\Omicron',     '\u039f'),
        (r'\Pi',          '\u03a0'),
        (r'\Rho',         '\u03a1'),
        (r'\Sigma',       '\u03a3'),
        (r'\Tau',         '\u03a4'),
        (r'\Upsilon',     '\u03a5'),
        (r'\Phi',         '\u03a6'),
        (r'\Chi',         '\u03a7'),
        (r'\Psi',         '\u03a8'),
        (r'\Omega',       '\u03a9'),
        (r'\alpha',       '\u03b1'),
        (r'\beta',        '\u03b2'),
        (r'\gamma',       '\u03b3'),
        (r'\delta',       '\u03b4'),
        (r'\epsilon',     '\u03b5'),
        (r'\zeta',        '\u03b6'),
        (r'\eta',         '\u03b7'),
        (r'\theta',       '\u03b8'),
        (r'\iota',        '\u03b9'),
        (r'\kappa',       '\u03ba'),
        (r'\lambda',      '\u03bb'),
        (r'\mu',          '\u03bc'),
        (r'\nu',          '\u03bd'),
        (r'\xi',          '\u03be'),
        (r'\omicron',     '\u03bf'),
        (r'\pi',          '\u03c0'),
        (r'\rho',         '\u03c1'),
        (r'\sigma',       '\u03c3'),
        (r'\tau',         '\u03c4'),
        (r'\upsilon',     '\u03c5'),
        (r'\phi',         '\u03c6'),
        (r'\chi',         '\u03c7'),
        (r'\psi',         '\u03c8'),
        (r'\omega',       '\u03c9'),
    ]

    m = arg['content']
    for (t, s) in symbol:
        m = m.replace(t, s)
    send(m)

help = {
    'echo'           : 'echo <content> -- 我才不会自问自答呢!',
    'ping!'          : 'ping!',
    'pong!'          : 'pong!',
    'color'          : 'color -- let\'s puke \\x0304r\\x0307a\\x0308i\\x0303n\\x0310b\\x0302o\\x0306w\\x0fs!',
    'mode'           : 'mode -- \\x0300free\\x0f\\x0303node\\x0f is awesome!',
}

func = [
    (echo,            r"echo (?P<content>.*)"),
    (pong,            r"ping!"),
    (ping,            r"pong!"),
    #(ping2,           r"(?:.*): pong!"),
    (color,           r"color"),
    (mode,            r"mode"),
    (pia,             r"pia( (?P<content>.*))?"),
    (mua,             r"mua( (?P<content>.*))?"),
    (latex,           r"latex\s+(?P<content>.*)"),
]
