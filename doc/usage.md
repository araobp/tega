#tega CLI usage

```
           [tega db]
            |     |
            |     +----+
            |          |
       Terminal 1  Terminal 2
```

###Get with regular expressions
```
tega CLI (q: quit, h:help)
[tega: 0] get r-a
a: {x: 1, y: 2, z: 3}
b: {x: 4, y: 5, z: 6}

[tega: 1] get r-b
a: {x: 1, y: 2, z: 3}
b: {x: 4, y: 5, z: 6}

[tega: 2] getr r-(.*)
r-a:
  groups:
  - [a]
  instance:
    a: {x: 1, y: 2, z: 3}
    b: {x: 4, y: 5, z: 6}
r-b:
  groups:
  - [b]
  instance:
    a: {x: 1, y: 2, z: 3}
    b: {x: 4, y: 5, z: 6}

[tega: 3] getr (r)-(.*)\.(.*)
r-a.a:
  groups:
  - [r, a]
  - [a]
  instance: {x: 1, y: 2, z: 3}
r-a.b:
  groups:
  - [r, a]
  - [b]
  instance: {x: 4, y: 5, z: 6}
r-b.a:
  groups:
  - [r, b]
  - [a]
  instance: {x: 1, y: 2, z: 3}
r-b.b:
  groups:
  - [r, b]
  - [b]
  instance: {x: 4, y: 5, z: 6}

[tega: 4] getr r-(.*)\.(.*)
r-a.a:
  groups:
  - [a]
  - [a]
  instance: {x: 1, y: 2, z: 3}
r-a.b:
  groups:
  - [a]
  - [b]
  instance: {x: 4, y: 5, z: 6}
r-b.a:
  groups:
  - [b]
  - [a]
  instance: {x: 1, y: 2, z: 3}
r-b.b:
  groups:
  - [b]
  - [b]
  instance: {x: 4, y: 5, z: 6}

```

###Transaction
```
tega CLI (q: quit, h:help)
[tega: 0] begin
txid: 3083e119-5272-4881-9493-1da2a2de3ac0 accepted
[tega: 1] put r1
x: 1
y: 2

[tega: 2] del r1.y
[tega: 3] put r2
x: 3
y: 4

[tega: 4] get r1
400 Bad Request
[tega: 5] get r2
400 Bad Request
[tega: 6] commit
txid: 3083e119-5272-4881-9493-1da2a2de3ac0 commited
[tega: 7] get r1
{x: 1}

[tega: 8] get r2
{x: 3, y: 4}

[tega: 9]
```

###Transaction with collision detection
```
<<<At Terminal 1>>>
tega CLI (q: quit, h:help)
[tega: 0] put r
a: 1
b: 2

[tega: 1] put r.b
3

[tega: 2] geta r.b
{_ephemeral: false, _oid: b, _parent: r, _value: 3, _version: 1}

[tega: 3] begin
txid: 0fba7dcb-2347-44f3-9d88-0ccfb0770ef2 accepted
[tega: 4] put r.b 1
4

[tega: 5] commit
406 Not Acceptable
id: 0fba7dcb-2347-44f3-9d88-0ccfb0770ef2 rejected

<<<At Terminal 2>>>
tega CLI (q: quit, h:help)
[tega: 0] geta r.b
{_ephemeral: false, _oid: b, _parent: r, _value: 3, _version: 1}

[tega: 1] begin
txid: ffeb8969-f6a2-4100-8ee7-f113dd7eff68 accepted
[tega: 2] put r.b 1
5

[tega: 3] commit
txid: ffeb8969-f6a2-4100-8ee7-f113dd7eff68 commited

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

###Messaging(pubsub) with regular expressions
```
<<<At Terminal 1>>
$ ./cli -s
tega CLI (q: quit, h:help)
[tega: 0] --- session ready ---
[tega: 1] subr r-\w*\.a       
[tega: 2] subscribers
GlobalPlugin1: [GlobalPlugin1]
d79feb02-3a81-4e7e-b37d-92dafc1f0a94: [r-\w*\.a]

[tega: 3] 
<NOTIFY>
[{'instance': 'XXX', 'tega_id': None, 'ope': 'PUT', 'path': 'r-a.a.x'}]
[tega: 4] 
<NOTIFY>
[{'instance': 'YYY', 'tega_id': None, 'ope': 'PUT', 'path': 'r-b.a.x'}]

<<<At Terminal 2>>
$ ./cli
tega CLI (q: quit, h:help)
[tega: 0] put r-a.a.x
XXX

[tega: 1] put r-b.a.x
YYY

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

