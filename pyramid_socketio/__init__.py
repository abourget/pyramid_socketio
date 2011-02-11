# Everything is in io.py because loading logging in the global scope would
# load the 'threading' module.. and it mustn't be loaded when serve.py and
# servereload.py are loaded, as they're going to monkey patch that module.
#
# To have serve.py and servereload.py under this package name, __init__
# was required *not* to load the logging module, that's why it's under
# io.py
