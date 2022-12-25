import asyncio
import time
import random
import math
import unicodedata
import re
import datetime


@asyncio.coroutine
def say(arg, send):
    #send(arg['content'])
    send('[{0}] '.format(arg['meta']['nick']) + arg['content'], raw=True)


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


class unicodenormalize:

    def __init__(self):
        #self.reg = re.compile(r"(?:[\u0300-\u036F]|[\u1AB0–\u1AFF]|[\u1DC0–\u1DFF]|[\u20D0–\u20FF]|[\uFE20–\uFE2F])+")
        # add Cyrillic combining characters
        self.reg = re.compile(r"(?:[\u0300-\u036F]|[\u1AB0–\u1AFF]|[\u1DC0–\u1DFF]|[\u20D0–\u20FF]|[\uFE20–\uFE2F]|[\u0483-\u0489])+")
        self.trans = str.maketrans(
            #'абвгдеёзийклмнопрстуфхъыьэАБВГДЕЁЗИЙКЛМНОПРСТУФХЪЫЬЭ',
            #'abvgdeezijklmnoprstufh y eABVGDEEZIJKLMNOPRSTUFH Y E',
            #'АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдежзийклмнопрстуфхцчшщъыьэюя',
            #'ABVGDEZZIJKLMNOPRSTUFHCCSS Y EUAabvgdezzijklnmoprstufhccss y eua',
            'еђгєѕіјљњћкиуџабвджзлмнопрстфхцчшщъыьэюяѡѣѥѧѩѫѭѯѱѳѵѹѻѽѿҁ҂ҋҍҏґғҕҗҙқҝҟҡңҥҧҩҫҭүұҳҵҷҹһҽҿӏӄӆӈӊӌӎӕәӡөӷӻӽӿ',
            'ehgesijbbhknyyabbaxeamhonpctpxyywwbbbeorwbeaaaaeptvyoowcxnbpgfhxekkkkhhhqctyyxyyyheelkahhymaeetgfxx',
            '\u200b\u200c\u200d\u200e\u200f\ufeff',
        )

    def __call__(self, s):
        return self.reg.sub('', unicodedata.normalize('NFKD', s.lower())).translate(self.trans)
unormalize = unicodenormalize()

@asyncio.coroutine
def pia(arg, send):
    content = arg['content'] or ''

    fullface = [
        '°Д°',
        '・ω・',
        '・∀・',
        '‵-′',
        '￣▽￣',
        '・_・',
        '>∧<',
        '´∀`',
        '°_°',
        '￣皿￣',
        '￣ω￣',
        '° △ °',
        '°ー°',
        '＠_＠',
        'T﹏T',
        '＞﹏＜',
        '┬＿┬',
        '￣︿￣',
        '╥﹏╥',
    ]
    face = [
        '°{}°',
        '・{}・',
        '‵{}′',
        '￣{}￣',
        '>{}<',
        '´{}`',
        '＠{}＠',
        'T{}T',
        '•̀{}•́',
        '艹{}艹',
        '^{}^',
        'X{}X',
        #'┬{}┬',
        #'╥{}╥',
    ]
    mouth = [
        'Д',
        'ω',
        '∀',
        '-',
        '▽',
        '_',
        '∧',
        '_>',
        '皿',
        '△',
        'ー',
        '﹏',
        '＿',
        '︿',
    ]
    face.extend([
        # csslayer
        'ˊ_>ˋ',
        # felixonmars
        '=﹁"﹁=',
        # frantic
        '>_<',
        # cuihao
        '=3=',
    ])
    icon = '(╯{0})╯ ┻━┻ '.format(random.choice(face).format(random.choice(mouth)))
    #if arg['meta']['bot'].nick not in content:
    #    send(icon + content)
    #else:
    #    send(icon + '不要 pia 我!')
    if 'orznzbot' in arg['meta']['nick']:
        return send(icon + '你才是!')
    if arg['meta']['bot'].nick.lower() in unormalize(content):
        send(icon + '不要 pia 我!')
    else:
        send(icon + content)


@asyncio.coroutine
def mua(arg, send):
    content = arg['content'] or ''

    #if arg['meta']['bot'].nick not in content:
    #    send('o(*￣3￣)o ' + content)
    #else:
    #    send('o(*￣3￣)o ' + '谢谢啦~')
    if arg['meta']['bot'].nick.lower() in unormalize(content):
        send('o(*￣3￣)o ' + '谢谢啦~')
    else:
        send('o(*￣3￣)o ' + content)


@asyncio.coroutine
def prpr(arg, send):
    content = arg['content'] or ''

    if arg['meta']['bot'].nick.lower() in unormalize(content):
        send('咦!')
    else:
        send('哧溜! ' + content)


@asyncio.coroutine
def hug(arg, send):
    content = arg['content'] or ''

    #if arg['meta']['bot'].nick not in content:
    #    send('(つ°ω°)つ ' + content)
    #else:
    #    send('(つ°ω°)つ ' + '谢谢啦~')
    if arg['meta']['bot'].nick.lower() in unormalize(content):
        send('(つ°ω°)つ ' + '谢谢啦~')
    else:
        send('(つ°ω°)つ ' + content)


@asyncio.coroutine
def color(arg, send):
    #c = [
    #    ('00', 'white'),
    #    ('01', 'black'),
    #    ('02', 'blue'),
    #    ('03', 'green'),
    #    ('04', 'red'),
    #    ('05', 'brown'),
    #    ('06', 'purple'),
    #    ('07', 'orange'),
    #    ('08', 'yellow'),
    #    ('09', 'light green'),
    #    ('10', 'teal'),
    #    ('11', 'light cyan'),
    #    ('12', 'light blue'),
    #    ('13', 'pink'),
    #    ('14', 'grey'),
    #    ('15', 'light grey'),
    #]
    c = [
        ('00', 'white'),
        ('01', 'black'),
        ('02', 'blue'),
        ('03', 'green'),
        ('04', 'light red'),
        ('05', 'red'),
        ('06', 'magenta'),
        ('07', 'orange'),
        ('08', 'yellow'),
        ('09', 'light green'),
        ('10', 'cyan'),
        ('11', 'light cyan'),
        ('12', 'light blue'),
        ('13', 'light magenta'),
        ('14', 'grey'),
        ('15', 'light grey'),
    ]
    if arg['all']:
        send(' '.join(['\\x03{0:0>#02}{0:0>#02}\\x0f'.format(x) for x in range(0, 50)]))
        send(' '.join(['\\x03{0:0>#02}{0:0>#02}\\x0f'.format(x) for x in range(50, 100)]))
    else:
        send('\\x02bold\\x02 \\x1ditalic\\x1d \\x1funderline\\x1f \\x06blink\\x06 \\x16reverse\\x16')
        #send('\\x07bell\\x07 \\x1bansi color\\x1b')
        send(' '.join(map(lambda x: '\\x03{0}{0} {1}\\x0f'.format(*x), c[:8])))
        send(' '.join(map(lambda x: '\\x03{0}{0} {1}\\x0f'.format(*x), c[8:])))


# provide a search?
@asyncio.coroutine
def mode(arg, send):
    u = [
        ('g', 'caller-id'),
        ('i', 'invisible'),
        ('Q', 'disable forwarding'),
        ('R', 'block unidentified'),
        ('w', 'see wallops'),
        ('Z', 'connected securely'),
    ]
    c = [
        ('b', 'channel ban'),
        ('c', 'colour filter'),
        ('C', 'block CTCPs'),
        ('e', 'ban exemption'),
        ('f', 'forward'),
        ('F', 'enable forwarding'),
        ('g', 'free invite'),
        ('i', 'invite only'),
        ('I', 'invite exemption'),
        ('j', 'join throttle'),
        ('k', 'password'),
        ('l', 'join limit'),
        ('m', 'moderated'),
        ('n', 'prevent external send'),
        ('p', 'private'),
        ('q', 'quiet'),
        ('Q', 'block forwarded users'),
        ('r', 'block unidentified'),
        ('s', 'secret'),
        ('S', 'SSL-only'),
        ('t', 'ops topic'),
        ('z', 'reduced moderation'),
    ]
    send('\\x0304user\\x0f ' + ' '.join(map(lambda e: '\\x0300{0}\\x0f/{1}'.format(*e), u)) + ' (see [\\x0302 https://freenode.net/kb/answer/usermodes \\x0f])')
    send('\\x0304channel\\x0f ' + ' '.join(map(lambda e: '\\x0300{0}\\x0f/{1}'.format(*e), c[:20])))
    send('\\x0304cont.\\x0f ' + ' '.join(map(lambda e: '\\x0300{0}\\x0f/{1}'.format(*e), c[20:])) + ' (see [\\x0302 https://freenode.net/kb/answer/channelmodes \\x0f])')


def getrandom(show):
    # http://en.wikipedia.org/wiki/Mathematical_constant
    # http://pdg.lbl.gov/2014/reviews/rpp2014-rev-phys-constants.pdf
    const = [
        # math
        (0,                              'zero'),
        (1,                              'unity'),
        ('i',                            'imaginary unit'),
        (3.1415926535,                   'pi'),
        (2.7182818284,                   'e'),
        (1.4142135623,                   'Pythagoras constant'),
        (0.5772156649,                   'Euler-Mascheroni constant'),
        (1.6180339887,                   'golden ratio'),
        # physics
        (299792458,                      'speed of light in vacuum'),
        (6.62606957,                     'Planck constant'),
        (1.054571726,                    'Planck constant, reduced'),
        (6.58211928,                     'Planck constant, reduced'),
        (1.602176565,                    'electron charge magnitude'),
        (0.510998928,                    'electron mass'),
        (9.10938291,                     'electron mass'),
        (938.272046,                     'proton mass'),
        (1.672621777,                    'proton mass'),
        (1836.15267245,                  'proton mass'),
        (8.854187817,                    'permittivity of free space'),
        (12.566370614,                   'permeability of free space'),
        (7.2973525698,                   'fine-structure constant'),
        (137.035999074,                  'fine-structure constant'),
        (2.8179403267,                   'classical electron radius'),
        (3.8615926800,                   'electron Compton wavelength, reduced'),
        (6.67384,                        'gravitational constant'),
        (6.70837,                        'gravitational constant'),
        (6.02214129,                     'Avogadro constant'),
        (1.3806488,                      'Boltzmann constant'),
        (8.6173324,                      'Boltzmann constant'),
        (1.1663787,                      'Fermi coupling constant'),
        (0.23126,                        'weak-mixing angle'),
        (80.385,                         'W boson mass'),
        (91.1876,                        'Z boson mass'),
        (0.1185,                         'strong coupling constant'),
        # other
        (9,                              'Cirno'),
        (1024,                           'caoliu'),
        (1984,                           'Orwell'),
        (10086,                          'China Mobile'),
        (233,                            'LOL'),
        (2333,                           'LOL'),
        (23333,                          'LOL'),
    ]
    rand = [
        # random
        (random.randint(0, 9),           'random number'),
        (random.randint(10, 99),         'random number'),
        (random.randint(100, 999),       'random number'),
        (random.randint(1000, 9999),     'random number'),
        (random.randint(10000, 99999),   'random number'),
        #math.sqrt(random.randint(0, 100000)),
    ]

    if show:
        get = lambda e: '{0} -- {1}'.format(str(e[0]), e[1])
    else:
        get = lambda e: str(e[0])
    l = random.choice([const, rand])
    return get(random.choice(l))


@asyncio.coroutine
def up(arg, send):
    send('+' + getrandom(arg['show']))


@asyncio.coroutine
def down(arg, send):
    send('-' + getrandom(arg['show']))


@asyncio.coroutine
def utc(arg, send):

    tz = arg['zone'] or '0'
    send(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=int(tz)))))


@asyncio.coroutine
def horo(arg, send):
    l = [
        '咱可是贤狼啊。起码还是知道这世界上有很多东西是咱所不了解的。',
        '人呐……在这种时候似乎会说『最近的年轻人……』呗。',
        '嗯。这么一想，或许好雄性的表现和好大人的表现互不相容。好雄性显得孩子气，而好大人显得窝囊。',
        '咱希望汝不要说得那么羡慕的样子。',
        '咱也一样……不，咱懂汝的心情。就是因为咱懂……所以咱更不想说出口……咱想，在旁人的眼中看起来，咱们俩也是一副蠢样子。',
        '不过，汝在那个瞬间带着那些麦子，站在那座村落的那个位置上，也算是偶然。世上没有什么事情比必然与偶然更难懂了，就像要懂得木头人的爱恋之情一样困难。',
        '这种话就算不是咱的耳朵，也听得出来是谎言。',
        '神、神总是这样。总是……总是这么不讲理？',
        '咱不想再碰到醒过来时，都见不到人的状况了……咱受够孤独了。孤独好冷。孤独……好让人寂寞。',
        '人们就是清醒时，也可能走路踩到别人的脚，更何况是睡着的时候。可是呐，这尾巴是咱的骄傲，也是证明咱就是咱的唯一铁证。',
        '草原上的狼。比人类好应付，至少能沟通。',
        '咱可是约伊兹的贤狼赫萝。',
        '狼群只会在森林里生活，而狗儿曾经被人类饲养过。这就是狼跟狗攻击性不同的地方。狼只知道人类会狩猎，人类是恐怖的存在。所以咱们狼时时刻刻都在思考，当人类进入森林时，咱们要采取什么样的行动。',
        '你说的是结果吧。要不是在卡梅尔森赚到了钱，我的财产早就真的被你吃光了。',
        '哼。俗话说一不做二不休，到时候咱也会很快地把汝吃进肚子里。',
        '当然，汝这个人非但没有求我教导，反而是个拼命想要抓住咱的缰绳的罕见大笨驴啊。虽然在成功率上没什么希望，不过汝肯定是想站在跟咱相同的高度上呗。咱一直都是独自呆在山上，我已经对从下面看着咱的目光感到厌倦了。',
        '如果你是贤狼，就应该战胜诱惑啊。',
        '虽然纵欲会失去很多东西，可是禁欲也不会有任何建设。',
        '人们就是清醒时，也可能走路踩到别人的脚，更何况是睡着的时候。可是呐，这尾巴是咱的骄傲，也是证明咱就是咱的唯一铁证。',
        '旅行唯有出发前最愉快；狗儿唯有叫声最吓人；女人唯有背影最美丽。随随便便地抛头露面，会坏了人家的美梦。这种事情咱做可不来。',
        '接下来要商谈，所以，您大可以朝对您有利的方向尽情地撒谎。不过，这只狼绝对比我聪明得多，它可以看出您的话背后再背后的意思。如果您说了欠缺考量的话，身高可是会缩短一大截的。您明白了吧？',
        '咱可是唯一的贤狼赫萝。人们畏惧咱、服侍咱，但害怕咱可就不像话了。',
        '咱可没有建立新故乡的想法。故乡就是故乡，重要的不是谁在那里，而是土地在哪里。而且，汝所担心的，就是咱不这样说吧？咱的故乡是能重新建立的吗？',
        '猪如果被奉承，连树都爬得上去；但如果奉承雄性，只会被爬到头顶上。',
        '咱会受不了。如果尾巴被卖了，咱会受不了。汝脸上怎么好像写着『只要是能卖的东西，我什么都卖』呐？',
        '虽然咱长久以来被尊为神，且被束缚在这块土地上，但咱根本不是什么伟大的神。咱就是咱。咱是赫萝。',
	#「嗯。那儿夏季短暂，冬季漫长，是个银白色的世界呢。」
	#「汝曾去过吗？」
	#「我去过最北端的地方是亚罗西史托，那是全年吹着暴风雪的恐怖地方。」
	#「喔，咱没听过。」
	#「那你曾去过哪里呢？」
	#「咱去过约伊兹，怎么着？」
	#罗伦斯回答一声「没事」后，硬是掩饰住内心的动摇。罗伦斯曾听过约伊兹这个地名。不过那是在北方大地的旅馆听来的古老传说里，所出现的地名。
	#「你是在那里出生的吗？」
	#「没错。不知道约伊兹现在变成什么样了，大伙儿过得好不好呢？」
        # unofficial
        '基本上，得记住的文字种类太多了。还有呐，莫名其妙的组合也太多了。虽然人类会说只要照着说话规则写字就好，但是这显然是骗人的呗。',
        '如果我也能够变身成女孩子就好了。',
        '如果您会变身成女孩子，八成会被赫萝吃掉。',
        '呵。毕竟咱这么可爱，人类的雄性也会为咱倾倒。不过呐，人类当中没有够资格当咱对象的雄性。如果有人敢碰咱，咱只要警告他『小心命根子』，任谁都会吓得脸色惨白。呵呵呵。',
        '……抱歉。',
	'汝和咱活着的世界可是大不相同啊。',
    ]
    send('「{}」'.format(random.choice(l)))


@asyncio.coroutine
def bidi(arg, send):
    if arg['content']:
        return send(arg['content'] + ' bidi')

    normal = [
        'bidi',
        'bidi' + '!' * random.randint(1, 5),
        'bidi' + '?' * random.randint(1, 5),
    ]
    short = [
        'bi',
        'bi' + '!' * random.randint(1, 5),
        'bi' + '?' * random.randint(1, 5),
        'di',
        'di' + '!' * random.randint(1, 5),
        'di' + '?' * random.randint(1, 5),
    ]
    audio = [
        'bidibidibi!',
        'bidi' * random.randint(1, 15),
        'bidi' * random.randint(1, 15) + '!' * random.randint(1, 10),
        'bidi' * random.randint(1, 15) + '?' * random.randint(1, 10),
        'bidi' * random.randint(1, 30),
    ]

    if random.randint(1, 100) <= 10:
        lang = random.choice(['en', 'zh', 'ja', 'eo', 'id', 'la', 'no', 'vi'])
        line = random.choice(audio)
        yield from arg['meta']['command']('gtran {}:audio {}'.format(lang, line), [], send)
    else:
        send(random.choice(random.choice([normal, normal, normal, normal, short, audio])))


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

help = [
    ('say'          , 'say <content>'),
    ('ping!'        , 'ping!'),
    ('pong!'        , 'pong!'),
    ('pia'          , 'pia [content] -- Каждая несчастливая семья несчастлива по-своему'),
    ('mua'          , 'mua [content] -- Все счастливые семьи похожи друг на друга'),
    ('color'        , 'color [all] -- let\'s puke \\x0304r\\x0307a\\x0308i\\x0303n\\x0310b\\x0302o\\x0306w\\x0fs!'),
    ('mode'         , 'mode -- \\x0300free\\x0f\\x0303node\\x0f is awesome!'),
    ('up'           , 'up [show] -- nice boat!'),
    ('down'         , 'down [show]'),
    ('utc'          , 'utc [+/- zone offset]'),
    ('bidi'         , 'bidi [content] -- bidibidibi!'),
]

func = [
    (say            , r"say (?P<content>.+)"),
    (pong           , r"ping!"),
    (ping           , r"pong!"),
    #(ping2          , r"(?:.*): pong!"),
    (color          , r"color(?:\s+(?P<all>all))?"),
    (mode           , r"mode"),
    (up             , r"up(?:\s+(?P<show>show))?"),
    (down           , r"down(?:\s+(?P<show>show))?"),
    (pia            , r"pia( (?P<content>.+))?"),
    (mua            , r"mua( (?P<content>.+))?"),
    (hug            , r"hug( (?P<content>.+))?"),
    (prpr           , r"prpr( (?P<content>.+))?"),
    #(utc            , r"utc(?:\s(?P<zone>([-+])?[0-9]+))?"),
    (horo           , r"horo"),
    (horo           , r"horohoro"),
    (bidi           , r"bidi(?:bidi)*( (?P<content>.+))?"),
    (latex          , r"latex\s+(?P<content>.+)"),
]
