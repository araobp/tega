#Guideline

##Modelling
If you use this database for CRUD operations in DevOps and if you also need atomicity for CRUD operations, three-tier tree structure is ideal from an implementational point of view. 
```
config-<router>.<service_module or rpc>.<args/kwargs>

[tree structure on tega db]
         |
         |
      NOTIFY
      ROLLBACK
      RPC
         |
         V
  [super command] (service module) - - - CRUD operations can be atomic
       | | |                             depending on your implementations.
   +---+ | +------+
   |     |        |
[cmd0][cmd1]...[cmdn] - - - operations at each commands are atomic
```

But, for read-only data, you may have many-tier tree structure.
```
stats-<router>.<service_module or rpc>.a.b.c.d...

[tree structure on tega db]
         ^
         |
        PUT
         |
         |
  [super command] (service module)
       | | |
   +---+ | +------+
   |     |        |
[cmd0][cmd1]...[cmdn]
```
