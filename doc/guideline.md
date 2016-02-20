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
operational-<router>.<service_module or rpc>.a.b.c.d...
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


operational-<router>.<service_module or rpc>.a.b.c.d...
stats-<router>.<service_module or rpc>.a.b.c.d...
raw-<router>.<rpc>.a.b.c.d...<args/kwargs>

[tree structure on tega db]
         |
         |
        RPC
         |
         V
  [super command] (service module)
       | | |
   +---+ | +------+
   |     |        |
[cmd0][cmd1]...[cmdn]

```

Or, you use tega db as sort of "global etc file", you may have many-tier tree structure. In this case, super command needs to restar its processes and fetch(GET) all the config data on tega db.
```
config-<router>.<service_module>.a.b.c.d...

[tree structure on tega db]
         |
         |
        GET
         |
         |
         |
         V
  [super command] (service module) - - - it restarts its processes every time
       | | |                             the data on tega db is changed.
   +---+ | +------+
   |     |        |
[cmd0][cmd1]...[cmdn] 
```
