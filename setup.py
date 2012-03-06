import os
import sys

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'pyramid',
    'gevent',
    'gevent-socketio',
    'gevent-websocket',
    'greenlet',
    ]

setup(name='pyramid_socketio',
      version='0.9',
      description='Gevent-based Socket.IO pyramid integration and helpers',
      long_description="DOCUMENTATION: https://github.com/abourget/pyramid_socketio\n\n---\n\n" +  CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pylons",
        "Framework :: BFG",
        "Topic :: Internet :: WWW/HTTP",
        ],
      author='Alexandre Bourget',
      author_email='alex@bourget.cc',
      url='https://github.com/abourget/pyramid_socketio',
      keywords='web wsgi pylons pyramid websocket python gevent socketio socket.io',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      entry_points="""\
      [console_scripts]
      socketio-serve-reload = pyramid_socketio.servereload:socketio_serve_reload
      socketio-serve = pyramid_socketio.serve:socketio_serve

      [paste.server_factory]
      sioserver = pyramid_socketio.pasteserve:server_factory
      sioserver_patched = pyramid_socketio.pasteserve:server_factory_patched

      """,
      )

