#!/usr/bin/env python3.4

from tega.tree import *

r1 = Cont('r1')
r1.a.b(id=1, name='alice').phone = '111-2222'
r1.a.b(id=2, name='bob').phone = '333-4444'
r1.c = 'phone book'

print(r1.qname_())
print(r1.a.qname_())
print(r1.a.b.qname_())
print(r1.a.b(id=1, name='alice').qname_())
print(r1.a.b(id=1, name='alice').phone.qname_())
