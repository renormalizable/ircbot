import asyncio
import time


@asyncio.coroutine
def echo(arg, send):
    send(arg[0])

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


help = {
    'ping!'          : 'ping!',
    'pong!'          : 'pong!',
    'color'          : 'color -- let\'s puke \\x0304r\\x0307a\\x0308i\\x0303n\\x0310b\\x0302o\\x0306w\\x0fs!',
}

func = [
    (pong,            r"ping!"),
    (ping,            r"pong!"),
    #(ping2,           r"(?:.*): pong!"),
    (color,           r"color"),
    #(echo,            r"(.*)"),
]
