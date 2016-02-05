tega db
=======

Project start: 2014/8/8

MD-SAL-like database for small PCs (incl. Raspberry Pi), written in Python:
- Tornado-based
- CRUD/RPC supported
- Transaction supported
- JSON-oriented (not YANG)
- Schema-less
- Extensible with plugins
- NAT traversal (HTTP/WebSocket)
- Python and Go driver

Design policy
-------------
- Simplicity rather than high-performance and rigid schema
- NOSQL for non big data (small data)
- Embeddable data base
- Easy-to-use APIs
- Concurrenty support with coroutine

Project goal
------------
![goal](https://docs.google.com/drawings/d/1CVeMUwvrKnbgvjriW0ftwnIMtjiMDlDMCEN0tPTSujs/pub?w=640&h=480)

Use cases
---------
- [NLAN](https://github.com/araobp/nlan)
- BBR remote config
- OpenWrt remote config
- Instant VPN (L2 or L3)
- IOT

![Deployment](https://docs.google.com/drawings/d/16z8YFQztsGXWacq8fWyVzs85UTjZqllIs-hGGwav9GY/pub?w=640&h=480)

Try it out
----------
You need to have python3.5 installed on your Debian/Ubuntu Linux.

```
$ cd
$ git clone http://github.com/araobp/tega
$ pip3.5 install tornado
$ pip3.5 install httplib2
$ pip3.5 install pyyaml
$ pip3.5 install readline
$ mkdir tega/scripts/var
```

Append the following line to your ~/.bashrc
```
export PYTHONPATH=$PYTHONPATH:$HOME/tega
```

Start tega server like this:
```
$ cd tega/scripts
$ ./global
```

Python3.4 users also require the following package:
```
$ pip3 install backports_abc
```

Test tega CLI:
```
$ cd tega/scripts
$ ./cli
```


Current architecture
--------------------
as of 2015/6/14
```
                           [cli.py]
                               |
                          [driver.py]
                               |  |
         +---------------------+  +-----------------------+
         |                                                |
     Tornado                                          Tornado 
     [server.py] ------------ REST/WebSocket ---------[server.py]
         :                                                : 
     [idb.py]...[tree.py]                             [idb.py]...[tree.py]
         :                                                :
     --------                                         --------
    /tega.db/                                        /tega.db/
   ---------                                        ---------
   commit-log                                       commit-log
```

Documentation
-------------
- [tree structure](./doc/tree.png)
- [operations to the tree](https://docs.google.com/drawings/d/1KOUuiQcosYpfEi4HyF7BYsiiSEW_2rJsZKy9xIPuIZQ/pub?w=960&h=720)
- [tree structure implemention: Cont class and its attributes](./doc/attributes.md)
- [tega message format](./doc/message-format.md)
- [tega db format](./doc/tega-db-format.md)
- [sync path and notifications](./doc/sync_path_and_notifications.md)
- [subscription scope](./doc/subscription_scope.md)
- [rpc routing](https://docs.google.com/drawings/d/1GHHYrF3s0MRypT_SxHkDAT-aFTfCtMh9NkqQrVEtvqo/pub?w=960&h=720)

TODO(2016/02/5)
----
## Design change

Since tega db is for network config, it is not a good idea to take AP.

![CP](https://docs.google.com/drawings/d/11fC2DojI9gzw-FV3NG8Ubh97sKm0RmWk-tNJBu1Tt-M/pub?w=600&h=480)

![Collision](https://docs.google.com/drawings/d/1D45tSElc7S4bnPCV_VLwJXua2O08Jv2gMqL4xeLaf2s/pub?w=600&h=480)

References
----------
* [OVSDB(RFC7047)](https://tools.ietf.org/html/rfc7047)
* [OpenDaylight MD-SAL datastore](https://wiki.opendaylight.org/view/OpenDaylight_Controller:MD-SAL:Architecture:DOM_DataStore) 
* [YANG(RFC6020)](https://tools.ietf.org/html/rfc6020)
* [ZooKeeper](https://www.usenix.org/legacy/event/atc10/tech/full_papers/Hunt.pdf)
* [Cassandra](http://wiki.apache.org/cassandra/ArticlesAndPresentations)
