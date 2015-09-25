#!/usr/bin/env python3.4

from tega.tree import Cont
from tega.idb import tx, get_log_cache 

r = Cont('r')
r.a(id=1).b[1].c = 1 
r.a(id=2).b[2].c = False
with tx() as t:
    t.put(r.a)

r = Cont('r')
r.a(id=2).b[2].c = True 
with tx() as t:
    t.put(r.a(id=2))

print('--- log cache ---')
print(get_log_cache())
# TODO: boolean values in the result is empty

