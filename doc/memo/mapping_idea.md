Mapping idea (tentative)
=======================

tega schema in YAML
-------------------

<pre>
# Python-import-like declaration
import:
   package1: [aaa, bbb]
# YANG-group-like declaration
group:
   group_x:
      vid:
         type: int
         min: 0
         max: 4095 
      vni:
         type: int
         min: 0
         max: 16777215 
# Schema declaration 
schema:
   root:                                         YANG container
      _root: true
      a:                                         YANG container 
         c: int                                  YANG leaf 
         d: str                                  YANG leaf
      b:                                         YANG list
         _indexes: [e]                           YANG key
         e:                                      YANG container 
            type: int                            YANG type
            min: 0                               YANG range
            max: 100                             YANG range
         f:                                      YANG leaf-list
            type: str                            YANG type
            pattern: "[a-zA-Z]+"                 YANG pattern
            length: 100                          YANG length
            list: true
         g: group_x                              YANG grouping
         h: aaa

</pre>


Mapping to OVSDB
----------------

<pre>

OVSDB tables tega objects
------------ ------------------------------------------------
. . . . . . . . . . . . . . . .
table 'root'          root
                       |
                   +---+-------+------------------+
                   |           |                  |
               attr 'a'     attr b'xxx'     attr b'yyy'
                   |           |                  |
. . . . . . . . .  V           |                  |
table 'a'          a           |                  |
single row         |           |                  |
               +---+-----+     |                  |
               |         |     |                  |
            attr 'c' attr 'd'  |                  |
               |         |     |                  |
              10     'hello'   |                  |
. . . . . . . . . . . . . . .  V                  V 
table 'b'                     b(e=1)             b(e=2)
multiple rows                  |                  |
                           +---+-----+        +---+-----+
                           |         |        |         |
                        attr 'e' attr 'f'  attr 'e' attr 'f'
                           |         |        |         |
                           1 ['alice', 'bob'] 2  ['john', 'paul', 'geroge', 'ringo']
. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .
</pre>


OVSDB schema in YAML
--------------------

<pre>
root:
   columns:
      a:
         type:
           key: {refTable: a, type: uuid}
           min: 0
           max: 1
      b:
         type:
           key: {refTable: b, type: uuid}
           min: 0
           max: unlimited
   isRoot: true
   maxRow: 1

a:
   columns:
       _parent:
         type:
           key: {refTable, root, type: uuid}
           min: 1
           max: 1
       c:
         type:
           key: {type: integer}
       d:
         type:
           key: {type: string}
b:
   columns:
       _parent:
         type:
           key: {refTable: root, type: uuid}
           min: 1
           max: 1
       e:
         type:
           key: {type: integer, minInteger: 0, maxInteger: 100}
           min: 0
           max: 1 
       f:
         type:
           key: {type: string}
           min: 0
           max: unlimited
   _indexes:
         - [e]


root.a.c = 10
root.a.d = 'hello'
root.xxx.e = 1
root.xxx.f = 'alice'
root.b(e=1).f = 'alice'
root.yyy.e = 2
root.yyy.f = 'bob'
root.b(e=2).f = 'bob'

(Note) root.b(e=1) gerenates uuid and creates xxx. After that, root.b(e=1) returns xxx.
</pre>

