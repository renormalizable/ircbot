import importlib

path = 'modules.'
files = ['timeoutdict', 'commands', 'admin']
modules = [importlib.reload(importlib.import_module(path + f)) for f in files]
table = dict(zip(files, modules))

privmsg = sum((getattr(m, 'privmsg', []) for m in modules), [])
