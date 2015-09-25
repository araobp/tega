#In-memory object database (idb)

##Transaction
tega-dbにおけるtransactionとは、一括でCRUD operationを実行する事。commit()により各オペレーションのログがtega.dbに追記され、また、in-memory DBを更新する。

```
with tx() as t:
    t.put(a.b.c)
    t.put(x.y.z)
    t.delete("e.f.g")
```
or
```
t = tx()
t.put(a.b.c)
t.put(x.y.z)
t.delete("e.f.g")
t.commit()
```

##Persistence
- "tega.db" へ追記型でlogを書きこむ。
- 再起動時に"tega.db"を読み込むことで、multi-versionなtreeをin-memoryに再構成

##Collision detection
- put(), delete()とも、versionチェックによるcollision detection機構を備える。しかし、これは、optimistic lockingであり、pessimistic lockingが必要な場合には対応できない。 
- Local DBとMaster DB間のsync時にはcollisionが発生する場合がある＝＞conflict resolution。

例： あるtransaction中に他のtransactionが割り込みcollision発生
```
transaction 1
with tx() as t:
  b = t.get('a.b')
  x = a.b.x
  result = yield (some other process)
  b.y = 2
  t.put(b.y)

transaction 2
with tx() as t:
  b = t.get('a.b')
  x = a.b.x
  b.y = 3
  t.put(b.y)
```