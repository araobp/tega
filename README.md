tega db
=======

Project start: 2014/8/8

An experimental project to study model-driven data base.

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
- python3
- tornado
- httplib2
- pyyaml
- enum34(<= python3.2)

References
----------
* [OVSDB(RFC7047)](https://tools.ietf.org/html/rfc7047)
* [OpenDaylight MD-SAL datastore](https://wiki.opendaylight.org/view/OpenDaylight_Controller:MD-SAL:Architecture:DOM_DataStore) 
* [YANG(RFC6020)](https://tools.ietf.org/html/rfc6020)
* [ZooKeeper](https://www.usenix.org/legacy/event/atc10/tech/full_papers/Hunt.pdf)
* [Cassandra](http://wiki.apache.org/cassandra/ArticlesAndPresentations)
* [MQTT](http://mqtt.org/)
