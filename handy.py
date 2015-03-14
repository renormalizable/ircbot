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

func = [
    (zhihu,           r"zhihu\s+(?P<url>.+)"),
    (pm25,            r"pm2.5\s+(?P<city>.+)"),
]
