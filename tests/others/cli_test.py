#!/usr/bin/env python3.4

from tega.tree import *
from tega.idb import *

router = Cont('router')
r = router.bgp[100]
r.neighbor['10.8.8.100'].remote_as = 100
r.neighbor['10.8.8.101'].remote_as = 101
with tx() as t:
    t.put(r)

for nb in r.neighbor:
    print('neighbor: {}, remote-as: {}'.format(nb, r.neighbor[nb].remote_as))

oid = r.neighbor['10.8.8.101']
with tx() as t:
    t.delete(oid)

