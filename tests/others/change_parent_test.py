#!/usr/bin/env python3.4

from tega.tree import *

r1 = Cont('r1')
r1.a.b(id=1, name='alice').phone = '111-2222'
r1.a.b(id=2, name='bob').phone = '333-4444'
r1.c = 'phone book'

r2 = Cont('r2')
r1.a.b(id=1, name='alice').change_(r2.a.b)

print(r1.walk_(internal=True))
print(r2.walk_(internal=True))

r1.a.b(id=2, name='bob').change_(r2.a.b)
print(r2.walk_(internal=True))
