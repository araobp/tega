##SESSION/SESSIONACK
```
               [client]                      [server]
                  |                             |
                  |----- SESSION -------------->|
                  |<---- SESSIONACK ------------|
  <-- on_init() --|                             |
                  |                             |

```

##SUBSCRIBE/UNSUBSCRIBE
```
               [client]                      [server]
                  |                             |
                  |----- SUSBSCRIBE ----------->|
                  |                             |
                  |----- UNSUSBSCRIBE --------->|
                  |                             |

```
##NOTIFY
```
               [client]                      [server]                      [client]
                  |                             |                             |
                  |<---- NOTIFY ----------------|--- MOTIFY ----------------->|
                  |<---- NOTIFY ----------------|
                  |<---- NOTIFY ----------------|
                  |                             |

```
##PUBLISH/MESSAGE
```
               [client]                      [server]                    [client] [client]
                  |                             |                             |      |
                  |----- PUBLISH -------------->|----- MESSAGE -------------->|      |
                  |                             |----- MESSAGE --------------------->|
                  |                             |

```

##ROLLBACK
```
               [client]                      [server]                      [client]
                  |                             |                             |
                  |<---- ROLLBACK---------------|--- ROLLBACK---------------->|
                  |<---- ROLLBACK---------------|
                  |<---- ROLLBACK --------------|
                  |                             |

```

##REQUEST/RESPONSE
```
               [client]                      [server]
                  |                             |
  --- api() ----->|                             |
                  |----- REQUEST -------------->|
                  |<---- RESPONSE --------------|
  <-- return -----|                             |
                  |                             |

```

