#!/usr/bin/env python3.4

from tega.tree import *

r = Cont('r')
print(r.a())
print(repr(r.b()))
print(r.walk_(internal=True))
print('')
oid = r.x.b(id=1)()
print(oid.qname_())
print(oid)
print(repr(oid))
print('')
print(r.walk_(internal=True))
r.y.c(id=1).d=1
print('')
print(r.walk_(internal=True))

