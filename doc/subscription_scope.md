##SCOPE.LOCAL
```
plugin       [local idb]                  [global idb]
driver       idb server
    |         |     |                         |
    |-- SUB ->|     |                         |
```

##SCOPE.GLOBAL
```
plugin       [local idb]                  [global idb]
driver       idb server                    server  idb
    |         |     |                         |     |
    |-- SUB ->|-----|-- SUB ----------------->|---->|
```
