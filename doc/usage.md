#tega CLI usage

```
           [tega db]
            |     |
            |     +----+
            |          |
       Terminal 1  Terminal 2
```
###Messaging(pubsub)
```
<<<At Terminal 1>>>
$ ./cli -s
tega CLI (q: quit, h:help)
[tega: 0] --- session ready ---
[tega: 1] subscribe ch1
[tega: 2] 
<MESSAGE>
channel: ch1
tega_id: 4b13cc27-a301-47e8-a88d-1fe36ea4ba42

Good Morning!

<<<At Terminal 2>>
$ ./cli -s
tega CLI (q: quit, h:help)
[tega: 0] --- session ready ---
[tega: 1] publish ch1
Good Morning!

```

###Taking a snapshot
```
$ ./cli
tega CLI (q: quit, h:help)
[tega: 0] put a.b.c
1

[tega: 1] put a.x.y
"alice"

[tega: 2] get a
b: {c: 1}
x: {y: alice}

[tega: 3] ss
200 OK
```

###Manipulating ephemeral nodes
```
<<<At Terminal 1>>>
$ ./cli -s
tega CLI (q: quit, h:help)
[tega: 0] --- session ready ---
[tega: 1] subscribe a.b
[tega: 2] 
<NOTIFY>
[{'path': 'a.b.c', 'ope': 'PUT', 'tega_id': 'e9060b10-28f2-429e-9007-adb886a4b35e', 'instance': 1}]
[tega: 3] 
<NOTIFY>
[{'path': 'a.b.c', 'ope': 'DELETE', 'tega_id': None, 'instance': 1}]
[tega: 4] 

<<<At Termianl 2>>>
$ ./cli -s
tega CLI (q: quit, h:help)
[tega: 0] --- session ready ---
[tega: 1] pute a.b.c
1

[tega: 2] put a.x
2

[tega: 3] get a
b: {c: 1}
x: 2

[tega: 4] q

$ ./cli -s
tega CLI (q: quit, h:help)
[tega: 0] --- session ready ---
[tega: 1] get a
{x: 2}
```
