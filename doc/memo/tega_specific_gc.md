Garbage Collector
-----------------

I thought of using weakref, but it makes tega complicated.

tega-specific gc is required:

When an old root ages out, it executes the following code recursively:

if the child's version == my version:
   the child's _parent = null  # since the old root is to be deleted.
   del the reference to the childe 
