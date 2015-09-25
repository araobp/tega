Where does tega node's _parent point?
------------------------------------

version 0 tree:

Upward(_parent)
[idb(0)]<--[root(0)]<--[a(0)]<--[b(0)]

Downward(__doc__ attributes)
[idb(0)]-->[root(0)]-->[a(0)]-->[b(0)]

version 1 tree:

Upward(_parent)
[idb(0)]<--[root(1)]<--[a(1)]<--[b(1)]<--[c(1)]
[idb(0)]<--[root(0)]<--[a(0)]<--[b(0)]

Downward(__doc__ attributes)
[idb(0)]-->[root(1)]-->[a(1)]-->[b(1)]-->[c(1)]
         X [root(0)]-->[a(0)]-->[b(0)]           Snapshot isolation

version 2 tree:

Upward(_parent)
[idb(0)]<--[root(2)]<--[a(2)]<--[d(2)]<--[e(2)]
[idb(0)]<--[root(1)]<--[a(1)]<--[b(1)]<--[c(1)]
[idb(0)]<--[root(0)]<--[a(0)]<--[b(0)]

Downward(__doc__ attributes)
[idb(0)]---[root(2)]-->[a(2)]-->[d(2)]-->[e(2)]
                         +--------+
                                  |
                                  V
         X [root(1)]-->[a(1)]-->[b(1)]-->[c(1)]  Snapshot isolation
         X [root(0)]-->[a(0)]-->[b(0)]           Snapshot isolation


Consideration
-------------

As the time passes by, those parent nodes age out and are erased by Python's GC. No problem.

However, in some situations, it is neccesarry to keep _parent to an active parent:
* 'mount' a subtree onto a global tree.

From a _parent's point of view:

[idb(0)]<--[root(2)]<--[a(2)]<-mount-[d(2)]--[e(2)]
                       [a(2)]<-mount-[b(1)]--[c(1)]

From a __dict__'s point of view:

[idb(0)]-->[root(2)]-->[a(2)]-mount->[d(2)]--[e(2)]
                       [a(2)]-mount->[b(1)]--[c(1)]

That will be possible by making bi-directional link between nodes:
* a(2)'s __dict__ points to remote nodes: d(2) and b(1)
* The remote nodes's _parent attribute points to the parent node a(2).

So I need to create "RemoteRef" class to bridge those nodes:
* CRUD operations propagate to the remote nodes via RemoteRef objects.
* Notifications, RPCs and global/partial lock will also propagate.

Some sort of object serializetion technique will be required for that. Maybe I will use OrderedDict over JSON-RPC-like protocol that I am going to develop as well.

RemoteRef class replaces legacy network management protocols such as SNMP.

