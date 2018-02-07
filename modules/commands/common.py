
class Get:

    def __init__(self, add=None):
        self.line = []
        self.add = add or self.line.extend

    def __call__(self, l, n=-1, **kw):
        if n < 0:
            self.add(l.splitlines() or [''])
        else:
            for (i, m) in enumerate(l):
                self.add(m.splitlines() or [''])
                if n > 0 and i >= (n - 1):
                    break

    def str(self, sep='\n'):
        return sep.join(self.line)

class GetRaw:

    def __init__(self):
        self.result = []

    def __call__(self, l, n=-1, **kw):
        if n < 0:
            self.result.append(list(l))
        else:
            for (i, m) in enumerate(l):
                self.result.append(list(m))
                if n > 0 and i >= (n - 1):
                    break
            if not self.result:
                raise Exception()
