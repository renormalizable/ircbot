import importlib

path = 'modules.'
files = ['commands']
modules = [importlib.reload(importlib.import_module(path + f)) for f in files]

reply = modules[0].reply
