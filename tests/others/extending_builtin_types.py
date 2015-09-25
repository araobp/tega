#!/usr/bin/env python3.4

_primitive_types = [str, list, int, int, float, complex]
_attrs = {
        'get_parent': lambda self: getattr(self, '_parent'),
        'set_parent': lambda self, v: setattr(self, '_parent', v),
        'get_oid': lambda self: getattr(self, '_oid'),
        'set_oid': lambda self, v: setattr(self, '_oid', v),
        'get_version': lambda self: getattr(self, '_version'),
        'set_version': lambda self, v: setattr(self, '_version', v)
        }
types = {}

for type_ in _primitive_types:
    types[type_] = type('wrapped_'+str(type_)[7:][:-2], (type_,), _attrs)

for t,v in types.items():
    print(t, v)

s = 'aaa'
ns = types[type(s)](s)
ns.set_parent('me')
ns.set_version(10)
print(ns) 
print(ns.get_parent())
print(ns._parent)
print(ns.get_version())


i = 100 
ni = types[type(i)](i)
ni.set_parent('me')
print(ni) 
print(ni.get_parent())

l = [1, 2, 3] 
li = types[type(l)](l)
li.set_parent('me')
print(li) 
print(li.get_parent())
