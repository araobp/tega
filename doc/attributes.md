## Tree structure
```
    Cont --+-- Cont --+-- wrapped_str
           |          +-- wrapped_int
           |          +-- wrapped_tuple
           |          +-- Bool
           |
           +-- Cont --+-- Cont -- ...
           |          +-- Cont -- ...
           |               :
           |
           +-- Cont --+-- Cont (oid w/ no attributes)
           |
           +-- Cont --+-- RPC(Func)
```

## node attributes

### Cont class

|Attribute |Explanation                       |                                             |
|----------|----------------------------------|---------------------------------------------|
|(string)  |Reference to a child node         |An instance of Cont, Bool or RPC             |
|_parent   |Reference to the parent object    |GC may collect the parent                    |
|_oid      |Hash-able Key to the self object  |Such as str, int, long, tuple or frozendict  |
|_version  |Node version used for MVCC        |\__setattr\__ is disabled when _version > 0  |
|_ephemeral|Ephemeral node                    |True if it is ephemeral                      |
|_frozen   |Immutability                      |True as long as the attribute is immutable   |

### Bool(Cont) class

Bool class inherits all the attributes of Cont with an additional attribute as follows:

|Attribute |Explanation                       |                                             |
|----------|----------------------------------|---------------------------------------------|
|_value    |Reference to an value             |An instance of Bool(True or False)           |

### RPC(Cont) class

RPC class inherits all the attributes of Cont with an additional attribute as follows:

|Attribute |Explanation                       |                                             |
|----------|----------------------------------|---------------------------------------------|
|_value    |Reference to an object            |An instance of Func                          |

##Cont value: python built-in types

Built-in types are wrapped with wrapped_* classes. The main purpose of wrapping built-in classes is for version control.

For example, "str" is wrapped with "wrapped_str" class.

Note that those wrapped_* clases do not inherig Cont class.

```
root.a.b.c = object
Chained objects
root.__dict__['a'] --> a.__dict__['b'] --> b.__dict__['c'] --> wrapped object
```

## Cont value: function

Functions are wrapped with RPC class that is a child class of Cont.
```
root.a.b.c = Func
Chained objects
root.__dict__['a'] --> a.__dict__['b'] --> b.__dict__['c'] --> RPC.__dict__['_object'] --> Func
```

## Cont attribute: _parent

_parent points to its parent. You can reach its root parent by tarversing on _parent attributes recursively. 
```
root.a.b.c returns c
c.__dict__['_parent'] -- points to --> b
b.__dict__['_parent'] -- points to --> a
a.__dict__['_parent'] -- points to --> root

c.qname_() returns ['root', 'a', 'b', 'c']
b.qname_() returns ['root', 'a', 'b']

with tx() as t:
　　root.a.b.c = 1
  t.put(c) ==> qname:['root', 'a', 'b', 'c'] is generated from c as a path parameter for CRUD operations on tega db
  t.put(b) ==> qname:['root', 'a', 'b'] is generated from b as a path parameter for CRUD operations on tega db

```
