Why not use Python descriptors and meta classes?
------------------------------------------------

Google's protocolbuf seems to use Python descriptors and metaclasses to automatically generate getter/setter at runtime.

This technique is more concreate and powerful than sticking to __getattr__, __setattr__ and __delattr__.

The current implementation of tega uses __getattrr__, __setattr__ and __delattr__, since the getter/setter approach seems to consume more memory.

However, the current implementation has some drawback:
- a.b.c.delete_() seems ugly: the underscore is necessary to avoid collision with an attribute name 'delete'.

Fortunately, delete_() is rarely used and the inmemory DB implementation 'idb.py' supports delete() method.

Auto-generated descriptors
--------------------------
Pros:
- much more concrete and powerful.

Cons:
- Requires to restart the in-memory DB everytime you update the schema.
In case of OpenDaylight MD-SAL's datastore, OSGi loads new version of schema as an bundle, but you cannot mix different versions of same schema to construct data.
- Consumes more memory.



