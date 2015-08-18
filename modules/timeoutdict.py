import asyncio
from collections.abc import MutableMapping

class TimeoutDict(MutableMapping):

    def __init__(self, timeout=60):
        self.loop = asyncio.get_event_loop()

        self.d = {}
        self.timeout = timeout

    def __getitem__(self, key):
        return self.d.__getitem__(key)[0]

    def __setitem__(self, key, value):
        try:
            item = self.d.__getitem__(key)
            item[0] = value
            item[1].cancel()
            item[1] = self.__timeout__(key)
        except KeyError:
            self.d.__setitem__(key, [value, self.__timeout__(key)])

    def __delitem__(self, key):
        self.d.pop(key)[1].cancel()

    def __iter__(self):
        return self.d.__iter__()

    def __len__(self):
        return self.d.__len__()

    def __timeout__(self, key):
        return self.loop.call_later(self.timeout, lambda: self.__cleanup__(key))

    def __cleanup__(self, key):
        pass
        #self.pop(key, None)


#class TimeoutDict(MutableMapping):
#
#    def __init__(self, timeout=60):
#        self.loop = asyncio.get_event_loop()
#
#        self.d = {}
#        self.timeout = timeout
#
#    def __getitem__(self, key):
#        print('getitem')
#        return self.d.__getitem__(key)[0]
#        #item = self.lines.pop(nick, None)
#        #if item:
#        #    item[1].cancel()
#        #    return item[0]
#        #else:
#        #    return []
#
#    def __setitem__(self, key, value):
#        print('setitem')
#        try:
#            item = self.d.__getitem__(key)
#            item[0] = value
#            item[1].cancel()
#            item[1] = self.__timeout__(key)
#        except KeyError:
#            self.d.__setitem__(key, [value, self.__timeout__(key)])
#        #if nick not in self.lines:
#        #    self.lines[nick] = [l, self.loop.call_later(self.timeout, lambda: self.lines.pop(nick, None))]
#        #else:
#        #    self.lines[nick][0].extend(l)
#        #item = self.lines.get(nick, None)
#        #if item:
#        #    item[0].extend(l)
#        #else:
#        #    self.lines[nick] = [l, self.loop.call_later(self.timeout, lambda: self.lines.pop(nick, None))]
#
#    def __delitem__(self, key):
#        print('delitem')
#        self.d.pop(key)[1].cancel()
#
#    def __iter__(self):
#        print('iter')
#        return self.d.__iter__()
#
#    def __len__(self):
#        print('len')
#        return self.d.__len__()
#
#    def __timeout__(self, key):
#        return self.loop.call_later(self.timeout, lambda: self.d.pop(key, None))

#class Line:
#
#    def __init__(self, timeout=60):
#        self.loop = asyncio.get_event_loop()
#
#        self.d = {}
#        self.timeout = timeout
#
#    def append(self, key, value):
#        try:
#            item = self.d[key]
#            item[0].extend(value)
#            item[1].cancel()
#            item[1] = self.__timeout__(key)
#        except KeyError:
#            self.d[key] = [value, self.__timeout__(key)]
#
#    def pop(self, key, default):
#        try:
#            item = self.d.pop(key)
#            item[1].cancel()
#            return item[0]
#        except KeyError:
#            return default
#
#    def __timeout__(self, key):
#        return self.loop.call_later(self.timeout, lambda: self.d.pop(key, None))

#class Queue:
#
#    def __init__(self):
#        self.loop = asyncio.get_event_loop()
#
#        self.queues = {}
#        self.timeout = 60
#
#    @asyncio.coroutine
#    def add(self, nick, msg, send, func):
#        if nick not in self.queues:
#             # no size limit for now
#             self.queues[nick] = asyncio.Queue()
#             yield from self.queues[nick].put((msg, send))
#             asyncio.async(func(nick))
#        else:
#             yield from self.queues[nick].put((msg, send))
#
#    @asyncio.coroutine
#    def get(self, nick):
#        if nick in self.queues:
#            item = yield from self.queues[nick].get()
#            #if self.queues[nick].empty():
#            #    self.queues.pop(nick, None)
#            return item
#        else:
#            return None
