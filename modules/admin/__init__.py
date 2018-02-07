import importlib


path = 'modules.admin.'
files = ['bot']
modules = [importlib.reload(importlib.import_module(path + f)) for f in files]


privmsg = [
    modules[0].reload,
    modules[0].status,
]
