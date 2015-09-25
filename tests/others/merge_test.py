#!/usr/bin/env python3.4

from tega.tree import *

print('--- r1 ---')
r1 = Cont('r1')
r1.a.b(id=1, name='alice').phone = '111-2222'
r1.a.b(id=2, name='bob').phone = '333-4444'
r1.c = 'phone book'
print(r1.walk_(True))

print('--- r2 ---')
r2 = Cont('r2')
r2.a.b(id=2, name='bob').phone = '333-5555'
r2.a.b(id=3, name='carol').phone = '555-6666'
r2.c = 'phone book (new)'
r2.d = 'maybe, next time'
print(r1.walk_(True))

print('--- r2 merges with r1 ---')
r1.merge_(r2)
print(r1.walk_(True))
