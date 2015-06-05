
class Get:
    def __init__(self, add=None):
        self.line = []
        self.add = add or self.line.extend
    def __call__(self, l, n=-1, **kw):
        if n < 0:
            self.add(l.splitlines())
        else:
            for (i, m) in enumerate(l):
                if n > 0 and i >= n:
                    break
                self.add(m.splitlines())
    def str(self, sep='\n'):
        return sep.join(self.line)
