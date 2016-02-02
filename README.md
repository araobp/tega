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

Design policy
-------------
- Simplicity rather than high-performance and rigid schema
- NOSQL for non big data (small data)
- Embeddable data base
- Easy-to-use APIs
- Concurrenty support with coroutine

Modeling
--------
- [Modeling technique](./doc/modeling.md)

Project goal
------------
![goal](https://docs.google.com/drawings/d/1CVeMUwvrKnbgvjriW0ftwnIMtjiMDlDMCEN0tPTSujs/pub?w=640&h=480)

Use cases
---------
- BBR remote config
- OpenWrt remote config
- Instant VPN (L2 or L3)
- IOT

![Deployment](https://docs.google.com/drawings/d/16z8YFQztsGXWacq8fWyVzs85UTjZqllIs-hGGwav9GY/pub?w=640&h=480)

Try it out
----------
You need to have python3.4 installed on your Debian/Ubuntu Linux.

```
$ cd
$ git clone http://github.com/araobp/tega
$ pip3 install tornado
$ pip3 install httplib2
$ pip3 install pyyaml
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
```
Requirements
------------
- python3.5
- tornado
- httplib2
- pyyaml
- enum34(<= python3.2)

Documentation
-------------
- [tree structure](./doc/tree.png)
- [tree structure implemention: Cont class and its attributes](./doc/attributes.md)
- [tega message format](./doc/message-format.md)
- [tega db format](./doc/tega-db-format.md)
- [sync path and notifications](./doc/sync_path_and_notifications.md)
- [subscription scope](./doc/subscription_scope.md)
- [Using protobuf](./doc/protobuf.md)

TODO(2016/01/10)
----
- develop tega driver for golang
- support DCN with two-phase commit
- use protobuf for data validation

References
----------
* [OVSDB(RFC7047)](https://tools.ietf.org/html/rfc7047)
* [OpenDaylight MD-SAL datastore](https://wiki.opendaylight.org/view/OpenDaylight_Controller:MD-SAL:Architecture:DOM_DataStore) 
* [YANG(RFC6020)](https://tools.ietf.org/html/rfc6020)
* [ZooKeeper](https://www.usenix.org/legacy/event/atc10/tech/full_papers/Hunt.pdf)
* [Cassandra](http://wiki.apache.org/cassandra/ArticlesAndPresentations)
* [MQTT](http://mqtt.org/)
