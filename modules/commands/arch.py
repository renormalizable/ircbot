from datetime import datetime, timezone, timedelta

from .tool    import xml


async def arch(arg, send):
    table = {
        'gpg': 'rm -rf /etc/pacman.d/gnupg && pacman-key --init && pacman-key --populate'
    }

    send(table.get(arg['key'], 'Σ(っ °Д °;)っ 怎么什么都没有呀'))


help = [
]

func = [
    (arch          , r"arch\s+(?P<key>.+)"),
]
