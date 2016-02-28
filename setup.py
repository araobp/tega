from setuptools import setup

setup(name='tega',
      version='0.1',
      packages=['tega', 'tega.driver', 'tega.cli'],
      entry_points={
        'console_scripts':
            ['tega-server=tega.server:main',
             'tega-cli=tega.cli:main']
      }
)
