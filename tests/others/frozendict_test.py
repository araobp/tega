#!/usr/bin/env python3.4

from tega.tree import *
from tega.idb import *
from tega.frozendict import *

def test(**kwargs):
    return frozendict(kwargs)

arg1 = {'a':1, 'b':2}
arg2 = {'b':2, 'a':1}

print(hash(test(**arg1)))
print(hash(test(**arg2)))
print(hash(test(a=1, b=2)))
print(hash(test(b=2, a=1)))

key1 = test(a=1, b=2)
key2 = test(a=1, b=3)
print(hash(key1))
print(hash(key2))
d = {}
d[key1] = {'name': 'alice', 'gender': 'female'}
d[key2] = {'name': 'bob', 'gender': 'male'}

print(d[key1])
print(d[key2])

key1 = test(a=1, b=2)
key2 = test(a=1, b=3)
print(d[key1])
print(d[key2])

for k,v in d.items():
    print(k,v)

