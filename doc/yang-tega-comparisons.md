##YANG-tega comparison

|YANG      |tega                                                          |
|----------|--------------------------------------------------------------|
|leaf      |int, str, list(tuple), Bool and Func                          |
|leaf-list |[ ]                                                           |
|container |Cont (note: Python dict is always converted into Cont)        |
|list      |(Unsupported intentionally, for keeping compatiblity with JSON|
|presence  |Cont with no value                                            |
|leafref   |qname (under study)                                           |


##How tega's data structure (tega.tree) works internally

|tega oid (object identifier)   |How it works internally                                |
|-------------------------------|-------------------------------------------------------|
|a.b.c...                       |a.\_\_getattr\_\_('b').\_\_getattr\_\_('c')...                 |
|a.b.c = 1                      |a.\_\_getattr\_\_('b').\_\_setattr\_\_('c', 1)                 |
|a.b.c = {'e':1}                |a.\_\_getattr\_\_('b').\_\_getattr\_\_('c').\_\_setattr\_\_('e', 1)|
|a.b.c = ['f', 'g']             |a.\_\_getattr\_\_('b').\_\_setattr\_\_('c', ['f', 'g'])        |
|a.b.c['name'] = 'alice'        |Corresponds to a.b.c.name = 'alice'                    |
|a.b.c = instance               |The instance is an instance of int, str, list(tuple), bool or any function|

