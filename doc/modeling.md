Modeling technique
------------------

From a data structure point of view, you had better use SQL, Cassandra or ZooKeeper, from a data structure point of view.

Teqhnique
---------
- Flat structure
- Tables independent on other tables (avoid JOIN as much as possible).

GOOD
----
- Relational database: SQL
- Column-oriented: Cassandra
- Key-Value-Store: Redis, ZooKeeper, etcd etc

BAD
---
Tree structure: this database (tega) and some other databases, but it is sometimes useful for certain use cases:
- abstract network modeling in a multi-vendor environment
- JSON document manipulation (MongoDB, tega etc)

Why is tree strucutre bad?
--------------------------
- hard to deal with data strucutre change
- maintenance cost is high
