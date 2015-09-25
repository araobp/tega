In-memory DB locking strategies
-------------------------------
Refer to http://www.agiledata.org/essays/concurrencyControl.html


Collision detection for the in-memory DB
----------------------------------------
* Every Cont and ListElm instance retains '_version' of itself and '_$versions' that holds '_version' of every child (of one of the Python primitive types) [Note 1]
* Refer to https://wiki.opendaylight.org/view/OpenDaylight_Controller:MD-SAL:Architecture:DOM_DataStore


[Note 1] Unlike YANG, tree7047 uses Python primitive types as 'leaf' and 'leaf-list', because it is much more powerful. Think of the following example:

<pre>
root --+-- a = Python int 1
       |
       +-- b = Python str 'hello'
       |
       +-- c(id=1) --+-- id = 1
       |             |
       |             +-- protoc = <an instance of protocol buf>
       |
       +-- c(id=2) --+-- id = 2
       |             |
       |             +-- protoc = <an instance of protocol buf>
             :

root = Cont('root', validate=False)
root.a = 1
root.b = 'hello'
root.c(id=1).protoc = <an instance of protocol buf>
root.c(id=2).protoc = <an instance of protocol buf>

root.c(id=1).protoc.serlalizeToString() generates a string...

or you could even store the serialized protocol buf instance like this:
root.c(id=1).protoc = <an instance of protocol buf>.serializeToString()
root.c(id=2).protoc = <an instance of protocol buf>.serliazedToString()

or you may even store serilized tega object like this:
root.c(id=1).tree7047 = <an instance of tree7047>.serialize_()
root.c(id=2).tree7047 = <an instance of tree7047>.serialize_()

tega can selialize the 'root' object into YAML, Python dict or JSON.

or you may use the standard Pickle package to selialize any Python objects.
</pre>

I am going to develop an interface to OVSDB and MySQL, so that any kinds of Python object can be stored in RDBMS, supporing tree-structured indexing.

