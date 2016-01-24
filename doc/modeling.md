Modeling technique
------------------

In general, from a data structure point of view, you had better use SQL, Cassandra or ZooKeeper.

BUT tree structure is used for modeling networking in some use cases.

Modeling teqhnique in general
-----------------------------
- Flat structure
- Tables independent on other tables (avoid JOIN as much as possible).

GOOD
----
- Relational database: SQL
- Column-oriented: Cassandra
- Key-Value-Store(KVS): Redis, ZooKeeper etc

I have used Redis, ZooKeeper and Cassandra in other projects. They are good data bases.

BAD
---
Tree structure: this database (tega) and some other databases, but it is sometimes useful for certain use cases:
- abstract network modeling in a multi-vendor environment
- JSON document manipulation (MongoDB, tega etc)
- modeling config data for networking
- Use cases where data base transaction is required

Why is tree strucutre bad?
--------------------------
- hard to deal with data strucutre change
- high maintenance cost

How to deal with tree structure with SQL, Column-Oriented or KVS
----------------------------------------------------------------
[SQL, Column-Oriented or KVS] ---- your code generates tree structure ----> [tree sturcture such as JSON]
