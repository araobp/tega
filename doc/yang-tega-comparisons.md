|YANG      |tega                                                    |
|----------|--------------------------------------------------------|
|leaf      |int, str, list(tuple), Bool and Func                    |
|leaf-list |[ ]                                                      |
|container |Cont (note: Python dict is always converted into Cont)  |
|list      |Cont                                                    |
|key       |str, int and frozendict                                 |
|presence  |oid w/o value (oid created by \_\_call\_\_(self))       |
|leafref   |qname (under study)                                     |


|tega oid (object identifier)   |How it works internally                                |
|-------------------------------|-------------------------------------------------------|
|a.b.c...                       |a.\_\_getattr\_\_('b').\_\_getattr\_\_('c')...                 |
|a.b.c(id=1, name='alice')...   |a.b.c[frozendict(id=1, name='alice')]                  |
|a.b.c = 1                      |a.\_\_getattr\_\_('b').\_\_setattr\_\_('c', 1)                 |
|a.b.c = {'e':1}                |a.\_\_getattr\_\_('b').\_\_getattr\_\_('c').\_\_setattr\_\_('e', 1)|
|a.b.c = ['f', 'g']             |a.\_\_getattr\_\_('b').\_\_setattr\_\_('c', ['f', 'g'])        |
|a.b.c['name'] = 'alice'        |Corresponds to a.b.c.name = 'alice'                    |
|a.b.c[0][1] = 'alice'          |Dimensional-variable-like oid auto-creation            |
|a.b.c(id=1, name='alice')()    |oid w/o value, corresponding to YANG presence          |
|a.b.c[key] = 'alice'           |The key is a int, str or frozendict object             |
|a.b.c = instance               |The instance is an instance of int, str, list(tuple) bool or any function|

