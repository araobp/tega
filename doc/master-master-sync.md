#Master-Master synchronization

##Master-Slave relationship
tega takes A(Availability) and P(Partition Tolerance).

Data change made on Master is automatically propagated to Slave.

tega provides "sync" command to check if Master and Slace are in sync or not. If not in sync, tega performs automatic conflict resolution.
```
                  [Master] <= read/write
                    /  \
               in sync  === network partition
                  /      \
read/write => [Slave]  [Slave] <= read/write is still possible
```

##Notifications
```
notifications: [{},...] includes each CRUD operation and rollback operation.
```

##Automatic synchronization with pubsub
```
            Master                                       Slave
              |                                            |
              |<--- SESSION session_id --------------------|
              |---- SESSION session_id ------------------->|
              |<--- SUBSCRIBE sync_path -------------------|
              |---- SUBSCRIBE sync_path ------------------>|
      CRUD -->|                                            |
              |---- NOTIFY [{},...] ---------------------->|
              |                                            |--> put/delete
              |                                       X <--|--> notify
              |                                            |
              |                                            |<-- CRUD        
              |<--- NOTIFY [{},...] -----------------------|
put/delete <--|                                            |
    notify <--|--> X                                       |
```

##Manual synchronization ("sync" command)
```
                                                    log_cache in idb
                                                   +--------------------------+
                                                   |                          |　sync confirmed
                                                   |    :                     |   |
                                                   |CRUD ope log              |   V
                                                   |sync conformer marker     | ----
                                                   |CRUD ope log              |   |
                                                   |CRUD ope log              | sync unconfirmed
                                                   |    :                     |   |
                                                   |sync confirmed marker     |   V
                                                   +--------------------------+ 

            Master                                       Slave
              |                                            | <= START
              |<- POST /_sync_check -----------------------|
              |        sync_path, digest                   |
case a) already in sync
              |---- 200 OK ------------------------------->|
                                                  sync confirmed => EXIT
case b) out of sync
              |---- 409 CONFLICT ------------------------->|
              |<- POST /_sync_db---------------------------|
              |        transactions                 sync start marker                   
              |                                            |
         Conflict                                          |
         resolution                                        |
       sync start marker
  rollback <--|                                            |
put/delete <--|                                            |
    notify <--|                                            |
 sync confirmed marker
              |---- 200 OK ------------------------------->|
              |     _transactions                          |
              |                                       Conflict
              |                                       resolution
              |                                            |--> rollback
              |                                            |--> put/delete
              |                                            |--> notify
                                                  sync confirmed maker => EXIT
```
## Sync start marker (TBD)
If sync_db fails, tega will check sync start marker to make further actions.
