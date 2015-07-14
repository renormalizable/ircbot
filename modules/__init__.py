import importlib

path = 'modules.'
files = ['commands', 'admin']
modules = [importlib.reload(importlib.import_module(path + f)) for f in files]

privmsg = sum((getattr(m, 'privmsg', []) for m in modules), [])
