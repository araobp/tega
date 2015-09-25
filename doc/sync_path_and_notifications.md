#sync_path and notifications

##sync_path
sync_path is a path on a tree to define a scope for data synchronization between Master and Slave.

Data modification (put/delete) is notified to a peer (from Slave to Master, or from Master to Slave).
```
                          a o
                           / \
(C) put/delete =>       b o   o
                         / \
(A) put/delete =>     c X   o
                       / \
(B) put/delete =>   d o   o
                     / \
                  e o   o

sync_path: a.b.c
```

##Data Change Notification patterns

|put/delete|notify|path   |
|----------|------|-------|
|(A)       |(A)   |a.b.c  |
|(B)       |(B)   |a.b.c.d|
|(C)       |(A)   |a.b.c  |
