tega db format
==============
```
?                                  <== COMMIT_START_MARKER
+--------------------------------+
| record                         |
+--------------------------------+
+--------------------------------+
| record                         |
+--------------------------------+
@timestamp:policy                  <== COMMIT_FINISH_MARKER
?                                  <== COMMIT_START_MARKER
+--------------------------------+
| record                         |
+--------------------------------+
+--------------------------------+
| record                         |
+--------------------------------+
@timestamp:policy                  <== COMMIT_FINISH_MAKRER
*{sync_path, url, version}         <== SYNC_CONFIRMED_MARKER
-1 root_oid                        <== ROLLBACK_MARKER
?                                  <== COMMIT_START_MARKER
+--------------------------------+
| record                         |
+--------------------------------+
                  :
```

Sample
```
- '?'
- {instance: ooo, ope: PUT, path: inventory.ne1.name, tega_id: ae195088-1a9b-417e-ad8c-02a3092151bc,
  version: 0}
- '@1434112046.1363673:!'
- {instance: Berlin, ope: PUT, path: inventory.ne1.address, tega_id: 23ed04b9-3742-45e9-a656-584906337aff,
  version: 1}
- '@1434112046.1363673:!'
- -1 inventory
```
