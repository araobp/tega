```
$ jupyter console
Jupyter Console 4.0.3

[ZMQTerminalIPythonApp] Loading IPython extension: storemagic

In [1]: from tega.driver import Driver

In [2]: d = Driver()

In [3]: d.get('a')
Out[3]: '<<class 'tega.tree.Cont'> _oid=a>'

In [4]: print(d.get('a'))
{'b': {'c': 1}}

In [5]: from tega.tree import Cont

In [6]: a = Cont('a')

In [7]: a.b.c = 2

In [8]: d.put(a.b.c)

In [9]: d.get('a')
Out[9]: '<<class 'tega.tree.Cont'> _oid=a>'

In [10]: print(d.get('a'))
{'b': {'c': 2}}

In [11]: d.delete('a')

In [12]: 
```
