#!/usr/bin/env python3.4

from tega.tree import *

r = Cont('r')
r['a'] = 1
r['b'] = 2
print(r.walk_())
print(r['a'])

r['c']['d'] = 'c and d'
print(r.walk_())
print(r['c']['d'])

r[0][1] = '0 and 1'
print(r.walk_())
print(r[0][1])
del r[0][1]
print(r.walk_())

