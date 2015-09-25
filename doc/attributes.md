##Tree structure
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

##node attributes

###Cont class

|Attribute |Explanation                       |                                             |
|----------|----------------------------------|---------------------------------------------|
|(string)  |Reference to a child node         |An instance of Cont, Bool or RPC             |
|_parent   |Reference to the parent object    |GC may collect the parent                    |
|_oid      |Hash-able Key to the self object  |Such as str, int, long, tuple or frozendict  |
|_version  |Node version used for MVCC        |\__setattr\__ is disabled when _version > 0  |
|_presence |Corresponds to YANG presence      |                                             |
|_frozen   |Immutability                      |True as long as the attribute is immutable   |

###Bool(Cont) class

Bool class inherits all the attributes of Cont with an additional attribute as follows:

|Attribute |Explanation                       |                                             |
|----------|----------------------------------|---------------------------------------------|
|_value    |Reference to an value             |An instance of Bool(True or False)           |

###RPC(Cont) class

RPC class inherits all the attributes of Cont with an additional attribute as follows:

|Attribute |Explanation                       |                                             |
|----------|----------------------------------|---------------------------------------------|
|_value    |Reference to an object            |An instance of Func                          |

##Built-in typesの収容

Version管理のため、Wrapped classにてbuilt-in typeのobjectを収容する。例えば、strであれば、wrapped_strクラスで収容。wrapped classはContクラスが定義するfunction群のプールで構成され、Contを継承(inherit)しない。
```
root.a.b.c = object
Chained objects
root.__dict__['a'] --> a.__dict__['b'] --> b.__dict__['c'] --> wrapped object
```

##Functionの収容

Contの子クラスであるRPC classがwrapperとなりFuncを収容する。
```
root.a.b.c = Func
Chained objects
root.__dict__['a'] --> a.__dict__['b'] --> b.__dict__['c'] --> RPC.__dict__['_object'] --> Func
```

##_parentの利用目的

* 任意のoidからQName(Qualified Name)を生成するとき、parent nodeへ向かってrecursiveへoid取得する時に使われる。QNameは内部でしか使用されないため、リスト型で表現する。

```
root.a.b.c は c を返す。
c.__dict__['_parent'] -- points to --> b
b.__dict__['_parent'] -- points to --> a
a.__dict__['_parent'] -- points to --> root

c.qname_() returns ['root', 'a', 'b', 'c']
b.qname_() returns ['root', 'a', 'b']

with tx() as t:
　　root.a.b.c = 1
  t.put(c) ==> cからqname:['root', 'a', 'b', 'c']をindexとして生成しin-memory DBのtreeを操作
  t.put(b) ==> cからqname:['root', 'a', 'b']をindexとして生成しin-memory DBのtreeを操作

```
