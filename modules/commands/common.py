
class Get:
    def __init__(self):
        self.line = []
    def __call__(self, l, n=-1, **kw):
        if n < 0:
            self.line.extend(l.splitlines())
        else:
            for (i, m) in enumerate(l):
                if n > 0 and i >= n:
                    break
                self.line.extend(m.splitlines())
    def str(self, sep='\n'):
        return sep.join(self.line)
