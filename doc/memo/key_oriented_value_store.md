key-oriented value store (kovs?)
===============================

Characteristics of tree data structure (tega) for network configuration
---------------------------------------------------------------------

* Sometimes a key does not have its value: _presence.
* Length of a key tends to be large and contains much more info than the value, unlike the case of document-oriented KVS such as MongoDB. 

<pre>
Example
-------
Key-only data (w/ no value): network.router.bgp(local_as=100).neighbor(remote_as=200)
</pre>

"key-oriented value store" (kovs?)  is what I need.


Requirements
------------

* Schema-less KVS based on OVSDB
* In-memory object datastore (tega) in charge of the ACID-part 

Strategy
--------

Defining schema for every tree node is a really nasty idea.

What I would need is a simple hash table on OVSDB with single fixed schema:

qname = ('root', 'a', 'x', '{id=1}')

<pre>
                     OVSDB as KVS 
                     (Single table)
                     +------------+ 
                     |            |
                     |------------|
hash(qname[:1]) ---->|/// row ////| attr: ('a', 'b')
                     |------------|
                          ...
                     |------------|
hash(qname[:2]) ---->|/// row ////| attr: ('x', 'y') 
                     |------------|
                          ...
                     |------------|
hash(qname[:3]) ---->|/// row ////| attr: ('{id=1}', '{id=2}')
                     |------------|
                     |            |
                          ...
                     |------------|
hash(qname)   ------>|/// row ////| attr: 'int(1)'
                     |------------|
                          ...
                     |            |
                     +------------+

</pre>

The number of rows = the number of vertices of tree-strucutre data.

Every row has the following attributes:
* hash: string / OVSDB uses this as an index for the table
* oid: string ( < 32 characters)
* attr: string 
* parent: integer (the parent's hash) 
* value: string (Python object)
* version: integer

There is another table to cope with hash collision. The table has the following attributes:
* qname: string / OVSDB uses this as an index for the table 
* oid: string ( < 32 characters)
* attr: string 
* parent: integer (the parent's hash) 
* version: integer


A OVSDB schema for that is rather static and will never be updated: like a schema-less KVS.


Hash collision detection
------------------------
Although hash collision seldom happens, here is the ususal way to detect a collision and select the right row:
<pre>
1. The first write (version = 1) detects a hash collision if there is already another row. 
2. The transaction sets the version = -1 to the row and jumps to another table.
3. Then adds a row to the table.

                     OVSDB as KVS 
                     (Single table)              index  Seperate table
                     +------------+                 |  +------------+ 
                     |            |           qname |  |/// row /// |
             index   |------------|                 V  |------------|
hash(qname1) --+     |/// row ////| version > 0        |/// row ////|
               |     |------------|                    |------------|
               |          ...                               ...
               |     |------------|                    |            |
hash(qname2) --+---->|/// row ////| version: -1        +------------+
                     |------------|
                          ...
                     |            |
                     +------------+
</pre>

(Reference) http://en.wikipedia.org/wiki/Hash_table 

How to avoide those rows to be GCed by OVSDB
---------------------------------------------
Idea
* A special table keeping "strong" reference to them, as I did in my neutron-lan project.

Hub[ref, ref, ref, ...] ===> Hash Table

                 [row]
                   ^
                   |
          [row]<-[hub]->[row]
                   |
                   V
                 [row]
