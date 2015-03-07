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

func = [
    (zhihu,           r"zhihu\s+(?P<url>.+)"),
]
