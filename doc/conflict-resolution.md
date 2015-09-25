2015/5/28

tega performs conflict resolution as if Master and Slave made a pessimistic lock for each transaction.

##CRUD dependency graph and unions of CRUD paths
![Collision Detection](https://docs.google.com/drawings/d/13Ex1I9KGIyU8U-HRMXOocjiLAjKfZbG01cxapEf46jc/pub?w=960&h=491)

##Conflict check with sha256 digest
```
Master                                            Slave
        sha256 digest of:
   <--- commiters after last sync within the scope of sync_path ----

        sha256 digest of:
   ---- commiters after last sync within the scope of sync_path --->
```
##Conflict resolution policy
```
a ~ d: union of all the paths in the transaction
+: WIN policy
-: LOST policy
!: Raise Exception policy (it is not in the fig)

If 409 Conflict:

Master                                   Slave
     <--- transactions since last sync within the scope ----
conflict resolution
     ---- transactions since last sync within the scope --->
                                 conflict resolution                      

```

##Collision patterns
```
Master    Slave      Further action
-----------------------------------------
a-        d+
rollback  NOP        filters out transactions since last sync from Slave

b+        c-
NOP       rollback   filters out transactions since last sync from Master

b+        d+         Raise Exception
NOP       NOP

a-        c-         None
rollback  rollback

a!                   Raise Exception

          b!         Raise Exception
```

## Conflict resolution implementation

def conflict_resolution(subscriber, sync_path, transactions):

https://github.com/araobp/tega/blob/master/tega/idb.py
