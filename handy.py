import asyncio
from tool import html

# html parse

@asyncio.coroutine
def zhihu(arg, send):
    print('zhihu')

    url = arg['url']

    arg['n'] = 1
    arg['url'] = url
    arg['xpath'] = '//*[@id="zh-question-answer-wrap"]/div/div[3]/div'

    return (yield from html(arg, send))

@asyncio.coroutine
def pm25(arg, send):
    print('pm25')

    city = {
        '北京': '1',
        '成都': '2',
        '广州': '3',
        '上海': '4',
        '沈阳': '5',
    }

    try:
        location = city[arg['city']]
    except:
        send('只有如下城市: '+ ', '.join(city.keys()))
        return

    url = 'http://www.stateair.net/web/post/1/{0}.html'.format(location)

    arg['n'] = 1
    arg['url'] = url
    arg['xpath'] = '//*[@id="content"]/div[2]/div[1]/div/div[3]/table/tbody'
    field = list(map(lambda x: ('./' + x, 'text', '{}'), ['tr[3]/td', 'tr[2]/td', 'tr[5]//span', 'tr[1]//span']))
    def format(l):
        e = list(l)[0]
        return [', '.join(e).replace('\n', '')]

    return (yield from html(arg, send, field=field, format=format))

class Get:
    def __init__(self):
        self.l = ''
    def __call__(self, l, n=-1, **kw):
        if n < 0:
            self.l += l
        else:
            l = list(l)[0]
            self.l += l[0]

@asyncio.coroutine
def man(arg, send):
    print('man')

    #section = arg.get('section')
    section = arg['section']
    name = arg['name']

    #if not section:
    #    search = 'http://www.die.net/search/?q={0}&sa=Search&ie=ISO-8859-1&cx=partner-pub-5823754184406795%3A54htp1rtx5u&cof=FORID%3A9'.format(name)
    #    tmp = {}
    #    tmp['n'] = 1
    #    tmp['url'] = search
    #    tmp['xpath'] = '//*[@id="cse"]/div/div/div/div[5]/div[2]/div/div/div[1]/div[1]/table/tbody/tr/td[2]/div[1]/a'
    #    f = [('./', 'data-ctorig', '{}')]
    #    get = Get()
    #    yield from html(tmp, get, field=f)
    #    url = get.l
    #else:
    #    url = 'http://linux.die.net/man/{0}/{1}'.format(section, name)

    url = 'http://linux.die.net/man/{0}/{1}'.format(section, name)

    arg['n'] = 1
    arg['url'] = url
    arg['xpath'] = '//head'
    field = [('./title', 'text_content', '{}'), ('./base', 'href', '[\x0302{}\x0f]')]

    return (yield from html(arg, send, field=field))

func = [
    (zhihu,           r"zhihu\s+(?P<url>.+)"),
    (pm25,            r"pm2.5\s+(?P<city>.+)"),
    #(man,             r"man(\s(?P<section>[1-8ln]))?\s+(?P<name>.+)"),
    (man,             r"man\s(?P<section>[1-8ln])\s+(?P<name>.+)"),
]
