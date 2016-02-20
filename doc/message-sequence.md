##SESSION/SESSIONACK
Synchronous
```
               [client]                      [server]
                  |                             |
                  |----- SESSION -------------->|
                  |<---- SESSIONACK ------------|
  <-- on_init() --|                             |
                  |                             |

```

##SUBSCRIBE/UNSUBSCRIBE
Asynchronous/sequencial
```
               [client]                      [server]
                  |                             |
                  |----- SUSBSCRIBE ----------->|
                  |                             |
                  |----- UNSUSBSCRIBE --------->|
                  |                             |

```
##NOTIFY
Asynchronous/sequencial
```
               [client]                      [server]                      [client]
                  |                             |                             |
                  |<---- NOTIFY ----------------|--- MOTIFY ----------------->|
                  |<---- NOTIFY ----------------|
                  |<---- NOTIFY ----------------|
                  |                             |

```
##PUBLISH/MESSAGE
Asynchronous/sequencial
```
               [client]                      [server]                    [client] [client]
                  |                             |                             |      |
                  |----- PUBLISH -------------->|----- MESSAGE -------------->|      |
                  |                             |----- MESSAGE --------------------->|
                  |                             |

```

##ROLLBACK
Asynchronous/sequencial
```
               [client]                      [server]                      [client]
                  |                             |                             |
                  |<---- ROLLBACK---------------|--- ROLLBACK---------------->|
                  |<---- ROLLBACK---------------|
                  |<---- ROLLBACK --------------|
                  |                             |

```

##REQUEST/RESPONSE
Synchronous
```
               [client]                      [server]
                  |                             |
  --- api() ----->|                             |
                  |----- REQUEST -------------->|
                  |<---- RESPONSE --------------|
  <-- return -----|                             |
                  |                             |

```

