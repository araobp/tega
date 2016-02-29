from tega.subscriber import SCOPE
from tega.messaging import request, REQUEST_TYPE
from tega.tree import Cont, RPC
from tega.util import path2qname, qname2path, dict2cont, subtree, deserialize, copy_and_childref, align_vector, commit_log_number, readline_reverse, edges, nested_regex_path

import copy
import collections
from enum import Enum
import hashlib
import logging
import os
import re
import datetime
from tornado import gen
import traceback
import uuid
import json 

now = datetime.datetime.now

VERSION = '_version'
COMMIT_START_MARKER = '?'
COMMIT_FINISH_MARKER = '@'
ROLLBACK_MARKER = '-'
SYNC_CONFIRMED_MARKER = '*'
OLD_ROOTS_LEN = 10

_idb = {}  # in-memory DB
_old_roots = {}  # old roots at every version
_log_dir = None  # Log directory
_log_fd = None  # Log file descriptor
_ephemeral_nodes = {}  # holder of ephemeral nodes

server_tega_id = None  # Server's tega ID
tega_ids = set()  # tega IDs of subscribers and plugins
channels = {}  # channels subscribed by subscribers
global_channels = {}  # channels belonging to global or sync scope
subscribers = {}  # subscribers subscribing channels
subscribe_forwarders = set()
old_roots_len = OLD_ROOTS_LEN  # The max number of old roots kept in idb 

def _commit_log_filename(tega_id, num):
    return 'log.{}.{}'.format(tega_id, str(num))

class OPE(Enum):
    '''
    CRUD operations
    '''
    POST = 1
    GET = 2
    PUT = 3
    DELETE = 4 
    SS = 5
    ROLLBACK = 6

class NonLocalRPC(Exception):
    '''
    "Non-local RPC called" exception.
    '''

    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return self.reason

def start(data_dir, tega_id, maxlen=OLD_ROOTS_LEN):
    '''
    Starts tega db
    '''
    global _log_fd
    global _log_dir
    global server_tega_id
    server_tega_id = tega_id
    _log_dir = os.path.join(os.path.expanduser(data_dir))
    num = commit_log_number(server_tega_id, _log_dir)
    filename = _commit_log_filename(server_tega_id, num)
    log_file = os.path.join(_log_dir, filename)
    try:
        _log_fd = open(log_file, 'a+')  # append-only file
    except FileNotFoundError:
        raise
    old_roots_len = maxlen

def is_started():
    '''
    True if a log file has already been opened.
    '''
    global _log_fd
    if _log_fd and not _log_fd.closed:
        return True
    else:
        return False

def stop():
    '''
    Stops tega db
    '''
    global _log_fd
    if _log_fd:
        _log_fd.close()

def clear():
    '''
    Empties tega-db file and in-memory DB
    '''
    global _log_fd, _log_dir, _idb, _old_roots, server_tega_id

    # Clears idb
    _idb = {}
    _old_roots = {}

    # Removes commit log files
    _log_fd.close()
    max_ = commit_log_number(server_tega_id, _log_dir)
    for i in range(0, max_ + 1):
        log_file = os.path.join(_log_dir, _commit_log_filename(server_tega_id, i))
        if os.path.exists(log_file):
            os.remove(log_file)

    # Reopens an empty commit log file
    log_file = os.path.join(_log_dir, _commit_log_filename(server_tega_id, 0))
    _log_fd = open(log_file, 'a+')  # append-onlyfile

def _backslash_dot(path):
    return re.sub('\.', '\\.', path)

def subscribe(subscriber, path, scope=SCOPE.LOCAL, regex_flag=False):
    '''
    subscribes a path as a channel
    '''
    if not regex_flag:
        path = _backslash_dot(path)
    if not path in channels:
        channels[path] = [subscriber]
    else:
        if not subscriber in channels[path]:
            channels[path].append(subscriber)
        else:
            logging.warn('channel already exists - {}'.format(path))
    if not subscriber in subscribers:
        subscribers[subscriber] = [path]
    else:
        if not path in subscribers[subscriber]:
            subscribers[subscriber].append(path)
    if scope == SCOPE.GLOBAL:
        global_channels[path] = scope
        if not subscriber in subscribe_forwarders:  # Not from a forwarder.
            for _subscriber in subscribe_forwarders:
                if subscriber != _subscriber:
                    _subscriber.on_subscribe(path, scope)

def unsubscribe(subscriber, path, regex_flag=False):
    '''
    unsubscribes a path as a channel
    '''
    if not regex_flag:
        path = _backslash_dot(path)
    if path in channels:
        channels[path].remove(subscriber)
        if not channels[path]:
            del channels[path]
            if path in global_channels:
                del global_channels[path]
    if subscriber in subscribers:
        subscribers[subscriber].remove(path)
        if not subscribers[subscriber]:
            del subscribers[subscriber]

def unsubscribe_all(subscriber):
    '''
    unsubscribe all channels
    '''
    if subscriber in subscribers:
        channels = [channel for channel in subscribers[subscriber]]
        for channel in channels:
            unsubscribe(subscriber, channel, regex_flag=True)
    else:
        logging.info('{} not subscribing any channels'.format(subscriber))

def add_ephemeral_node(tega_id, path):
    '''
    Adds an ephemeral node.
    '''
    if not tega_id in tega_ids:
        raise Exception('cannot add ephemeral node for unregisterred tega id')
    if not tega_id in _ephemeral_nodes:
        holder = set()
        _ephemeral_nodes[tega_id] = holder
    else:
        holder = _ephemeral_nodes[tega_id]
    holder.add(path)

def remove_ephemeral_node(tega_id, path):
    '''
    Removes an ephemeral node.
    '''
    if tega_id in _ephemeral_nodes:
        _ephemeral_nodes[tega_id].remove(path)
        if not _ephemeral_nodes[tega_id]:
            del _ephemeral_nodes[tega_id]

def get_ephemeral_nodes(tega_id):
    '''
    Returns an ephemeral node.
    '''
    if tega_id in _ephemeral_nodes:
        return _ephemeral_nodes[tega_id]
    else:
        return set()  # empty set

def add_tega_id(tega_id):
    tega_ids.add(tega_id)

def remove_tega_id(tega_id):
    holder = get_ephemeral_nodes(tega_id)
    with tx() as t:
        for path in holder.copy():
            t.delete(path)
            remove_ephemeral_node(tega_id, path)
    tega_ids.remove(tega_id)

def get_tega_ids():
    return tega_ids

def add_subscribe_forwarder(forwarder):
    '''
    Adds a subscribe forwarder belonging to SCOPE.GLOBAL.
    '''
    subscribe_forwarders.add(forwarder)

def remove_subscribe_forwarder(forwarder):
    '''
    Removes a subscribe forwarder belonging to SCOPE.GLOBAL.
    '''
    subscribe_forwarders.remove(forwarder)

def get_channels():
    '''
    returns channels.
    '''
    _channels = {}
    for path in channels:
        _channels[path] = [subscriber.tega_id for subscriber in channels[path]]
    return _channels

def get_subscribers():
    '''
    returns subscribers.
    '''
    _subscribers = {}
    for subscriber in subscribers.keys():
        _subscribers[subscriber.tega_id] = subscribers[subscriber]
    return _subscribers

def get_subscriber_instances(channel):
    if channel in channels:
        return channels[channel]
    else:
        return None

def get_global_channels():
    return global_channels

def get_subscribe_forwarders():
    return subscribe_forwarders

def get_subscriber_for_global_db():
    '''
    TODO: choose one in case of ACT-ACT.
    '''
    return list(get_subscribe_forwarders())[0]

def get_subscriber_for_local_db(path):
    '''
    Returns a subscriber for local idb having the path.
    '''
    dst_tega_id = get(path).lstrip('%').split('.')[0]
    subscribers = get_subscriber_instances(dst_tega_id)
    if subscribers:
        return subscribers[0]
    else:
        return list(get_subscribe_forwarders())[0]  # to global idb 

def is_subscribe_forwarder(tega_id):
    for subscriber in subscribe_forwarders:
        if subscriber.tega_id == tega_id:
            return True
    return False

def log_entry(ope, path, tega_id, instance, backto=None):
    '''
    Log entry
    '''
    if backto:
        return {'ope': ope,
                'path': path,
                'tega_id': tega_id,
                'instance': instance,
                'backto': backto}
    else:
        return {'ope': ope,
                'path': path,
                'tega_id': tega_id,
                'instance': instance}

def old_roots_deque():
    return collections.deque(maxlen=old_roots_len)

def _notify_broadcast(notify_batch, subscriber=None):
    '''
    Notifies CRUD operations in a batch to subscribers

    notify_batch: [subscriber, [log_entory, ...]]
    '''
    for _subscriber, notifications in notify_batch.items():
        if subscriber != _subscriber:
            _subscriber.on_notify(notifications)

class tx:
    '''
    tega-db transaction 
    '''

    def __init__(self, tega_id=None, subscriber=None):
        '''
        Note: subscriber includes tega_id. The user of this class w/o
        a subscriber client needs to set tega_id.
        '''
        self.crud_queue = []  # requested CRUD operations
        self.commit_queue = []  # operations to be commited 
        self.candidate = {}  # candidate subtrees in a transaction
        self.txid = str(uuid.uuid4())  # transaction ID
        self.notify_batch = {} 
        self.subscriber = subscriber
        if self.subscriber:
            self.tega_id = self.subscriber.tega_id
        else:
            self.tega_id = tega_id

    def __enter__(self):
        return self

    def __exit__(self, type_, value, traceback):
        if type_ is None:
            self.commit(write_log=True)

    def _instance_version_set(self, instance, version):
        '''
        Sets "version" to the instance recursively.
        '''
        instance._setattr(VERSION, version)
        instance_version_set = self._instance_version_set
        if isinstance(instance, Cont):
            for k,v in instance.items():
                if isinstance(v, Cont):
                    instance_version_set(v, version)
                else:
                    v._setattr(VERSION, version)

    def _copy_on_write(self, qname, above_tail=False):
        '''
        Copies the vertexes and edges for snapshot isolation.
        Or uses a copy in self.candidate if it already exists.

        Returns a new root and a tail node:
       
        Pattern A
        [_idb]--[  root  ]--[a]--[b]-...-[above_tail]--[tail]
         (A)      (B)              | copy
                                   V
        [_idb]--[new_root]--[a]--[b]-...-[above_tail]--[tail]
                  (C)
      
        Pattern B
        [_idb]--[  root  ]--[a]--[b] ->X go: False (D)
         (A)      (B)        | copy
                             V
        [_idb]--[new_root]--[a]--[b]-...-[above_tail]--[tail]
                  (C)        - extend ->
       
        '''
        original = _idb
        new_root = None
        tail = None
        root = None
        redirection = None 
        go = False
        no_copy = False
        prev_version = -1
        new_version = 0
        root_oid = qname[0]

        if root_oid in self.candidate:  # copy already exists
            prev_version, new_version, root, redirection = self.candidate[root_oid]
            new_root = root
            go = True
            no_copy = True  # operations performed on the copy
        elif not root_oid in original:  # the root does not exist in _idb  
            new_root = Cont(root_oid)
        else:  # the root exists in _idb but its copy is not in self.candidate
            root = original[root_oid]
            prev_version = root._getattr(VERSION)
            new_version = prev_version + 1
            new_root, childref = copy_and_childref(root)
            redirection = [(root, childref)]
            go = True

        original = root
        tail = new_root
        
        if above_tail:
            qname = qname[:-1]

        if len(qname) == 0:
            new_root = tail = None
        else:
            for iid in qname[1:]:
                parent = tail
                if go and iid in original:
                    original = original._extend(iid)
                    if no_copy:
                        tail = original
                    else:
                        tail, childref = copy_and_childref(original)
                        redirection.append((original, childref))
                    tail._setattr('_parent', parent)
                    parent._setattr(iid, tail)
                else:
                    go = False
                    tail = parent._extend(iid)
                parent._setattr(VERSION, new_version)

            tail._setattr(VERSION, new_version)
            
        return prev_version, new_version, new_root, tail, redirection

    def commit(self, write_log=True):
        '''
        Transaction commit

        Note: since this data base is based on Tornado/coroutine,
        this commit function never interrupted by another process or thread.
        '''

        global _log_fd
        write = _log_fd.write

        for crud in self.crud_queue:
            func = crud[0]
            crud[0](*crud[1:])

        if len(self.commit_queue) > 0:
            finish_marker = COMMIT_FINISH_MARKER+'{}'.format(now())
            if write_log:  # Writes log
                if _log_fd:
                    _log_fd.write(COMMIT_START_MARKER+'\n')  # commit start
                    for log in self.commit_queue:
                        log = str(log)
                        write(log+'\n')
                    write(finish_marker+'\n')  # commit finish marker
                    _log_fd.flush()
                    os.fsync(_log_fd)

        # old roots cache update
        for root_oid in self.candidate:
            prev_version, new_version, new_root, redirection = self.candidate[root_oid]

            # Attaches the existing children (excluding newborns)
            if redirection:
                for r in redirection:
                    parent = r[0]
                    children = r[1]
                    for c in children:
                        c._setattr('_parent', parent)

            old_root = None
            if root_oid in _idb:
                old_root = _idb[root_oid]
            if new_root:
                _idb[root_oid] = new_root
            else:
                del _idb[root_oid]
            if old_root:
                if not root_oid in _old_roots:
                    _old_roots[root_oid] = old_roots_deque() 
                _old_roots[root_oid].append((prev_version, old_root))

        # Notifies the commited transaction to subscribers
        _notify_broadcast(notify_batch=self.notify_batch,
                subscriber=self.subscriber)
        self.notify_batch = {}

    def _enqueue_commit(self, ope, path, tega_id, instance, ephemeral):
        '''
        Appends CRUD to the commit queue.
        '''
        if not tega_id:  # CRUD by a subscriber of this server
            tega_id = self.tega_id
        else:
            pass  # CRUD initiated by a notification or a tega db driver.

        if instance and isinstance(instance, Cont):
            instance = instance.serialize_()

        log = log_entry(ope=ope.name, path=path, tega_id=tega_id, instance=instance)

        if not ephemeral:
            self.commit_queue.append(log)

        self._notify_append(log)

    def put(self, instance, tega_id=None, version=None, deepcopy=True,
            path=None, ephemeral=False):
        '''
        PUT operation.

        Set "version" to the one from GET operation, when collision check is
        required.
        '''
        if isinstance(instance, dict):
            instance = subtree(path, instance)
        self.crud_queue.append((self._put, instance, tega_id, version, deepcopy,
            ephemeral))

    def _put(self, instance, tega_id=None, version=None, deepcopy=True,
            ephemeral=False):

        qname = instance.qname_()
        path = qname2path(qname)
        if not tega_id:
            tega_id = self.tega_id

        if deepcopy:
            instance = instance.deepcopy_()

        if ephemeral:
            instance.ephemeral_()
            try:
                instance_ = get(path)
                if not instance_.is_ephemeral_():
                    raise Exception('non-ephemeral node cannot be ephemeral')
            except KeyError:
                pass
            add_ephemeral_node(tega_id, path)
        if version and _collision_check(qname, version):
            raise ValueError('collision detected')
        else:
            #
            # PUT OPERATION
            #
            #       _idb               _idb
            #       /       copy   (E) / / (F)
            #      o root(A)  o       o O ..> [Old roots]
            #    /   \   ..>   \  ..>  \
            #   o     o   (B)   o       o
            #  / \   / \               / \
            # o   o o   o             X   o
            #       ^             set version (C)
            #       |             change parent(replace) (D)
            #      put operation
            #
            if isinstance(instance, Cont):
                instance.freeze_()
            root_oid = qname[0]
            prev_version, new_version, new_root, above_tail, redirection = self._copy_on_write(qname, above_tail=True)
            self._instance_version_set(instance, new_version)

            if above_tail:
                instance.change_(above_tail)
            else:
                new_root = instance
            if not root_oid in self.candidate:
                self.candidate[root_oid] = (prev_version, new_version, new_root,
                        redirection)

            # Commit queue
            self._enqueue_commit(OPE.PUT, path, tega_id, instance, ephemeral)

    def delete(self, path, tega_id=None, version=None):
        '''
        DELETE operation.

        "path" can be either an instance of Cont or string.
        '''
        self.crud_queue.append((self._delete, path, tega_id, version))

    def _delete(self, path, tega_id=None, version=None):

        qname = None
        if not tega_id:
            tega_id = self.tega_id

        if isinstance(path, Cont):
            qname = path.qname_()
        else:
            qname = path2qname(path)

        if version and _collision_check(qname, version):
            raise ValueError('collision detected')
        else:

            #
            # DELETE OPERATION
            #
            #       _idb               _idb
            #       /       copy   (D) / / (E)
            #      o root(A)  o       o O ..> [Old roots]
            #    /   \   ..>   \  ..>  \
            #   o     o   (B)   o       o (C) del the attribute
            #  / \   / \                 \
            # o   o o   o             X   o
            #       ^
            #       |
            #      delete operation
            #
            root_oid = qname[0]
            prev_version, new_version, new_root, above_tail, redirection = self._copy_on_write(qname, above_tail=True)
            if above_tail:
                oid = qname[-1]
                instance = above_tail[oid]
                #del above_tail[oid]
                above_tail._delattr(oid)
                if above_tail.is_empty():
                    above_tail.delete_()
            else:
                instance = _idb[path]

            if not root_oid in self.candidate:
                self.candidate[root_oid] = (prev_version, new_version, new_root,
                        redirection)

            # Commit queue
            ephemeral = instance.is_ephemeral_()
            if ephemeral:
                remove_ephemeral_node(tega_id, path)
            self._enqueue_commit(OPE.DELETE, path, tega_id, instance, ephemeral)

    def get_candidate(self):
        '''
        Returns a candidate config.
        '''
        return [i[2].serialize_(internal=True) for k,i in self.candidate.items()]

    def _notify_append(self, log):
        '''
        Appends a CRUD operation as notifications to subscribers
        '''
        path = log['path']
        instance = log['instance']
        qname = path2qname(path)

        # Searches "path" in "channels".
        # Example:
        # regex_path = 'a\.b.\c'
        for regex_path in channels:

            nested = nested_regex_path(regex_path)
            
            are_parents_or_me = re.match(nested+'$', path) # (A)a.b or (B)a.b.c
            are_children = re.match(regex_path+'\.', path) # (C)a.b.c.d

            if are_parents_or_me:
                #print(are_parents_or_me.groups())
                idx = 1
                for elm in are_parents_or_me.groups():
                    if elm:
                        idx += 1
                    else:
                        break
                sub_qname = regex_path.split('\.')[idx:]
                #print(are_parents_or_me.groups())
                #print(sub_qname)
                for regex_oid in sub_qname:
                    for oid in instance:
                        # TODO: regex matching multiple children
                        if re.match(regex_oid, oid):
                            instance = instance[oid]
                            path += '.' + oid
                        else:
                            break
                        log['path'] = path
                        log['instance'] = instance

            if are_parents_or_me or are_children:
                for subscriber in channels[regex_path]:
                    try:
                        if not subscriber in self.notify_batch:
                            self.notify_batch[subscriber] = []
                        self.notify_batch[subscriber].append(log)
                    except:
                        traceback.print_exc()
                        logging.warn('subscriber removed - {}'.
                                format(subscriber))
                        channels[_path].remove(subscriber)

def _fetch_root_with_version(root_oid, version):
    root = _idb[root_oid]
    highest = root._version
    if version is None or version == highest:
        return root
    else:
        root = None
        if version < 0:
            version = highest + version
        for tup in _old_roots[root_oid]:
            if tup[0] == version:
                root = tup[1]
        if root:
            return root
        else:
            raise KeyError

def _select(original, regex_qname, regex_groups):
    '''
    Selects children.
    '''
    regex_oid = regex_qname[0]
    for k, v in original.items():
        m = re.match(regex_oid, k)
        if m:
            g = m.groups()
            if g:
                regex_groups_ = copy.copy(regex_groups)
                regex_groups_.append(g)
            else:
                regex_groups_ = regex_groups
            if isinstance(original, Cont) and len(regex_qname) > 1:
                yield from _select(v, regex_qname[1:], regex_groups_)
            else:
                yield (qname2path(v.qname_()), v, regex_groups_)

def get(path, version=None, regex_flag=False):
    '''
    GET operation.

    Raises KeyError if path is not found in idb.
    '''
    try:
        if regex_flag:
            regex_qname = path.split('\.')
            regex_oid = regex_qname[0]
            instances = []
            for root_oid in _idb:
                m = re.match(regex_oid, root_oid)
                if m:
                    regex_groups = []
                    g = m.groups()
                    if g:
                        regex_groups.append(g)
                    instance = _fetch_root_with_version(root_oid, version)
                    if len(regex_qname) > 1:
                        g = _select(instance, regex_qname[1:], regex_groups)
                        for match in g:
                            instances.append(match)
                    else:
                        instances.append((root_oid, instance, regex_groups))
            return instances
        else:
            qname = path2qname(path)
            root_oid = qname[0]
            instance = _fetch_root_with_version(root_oid, version)
            if len(qname) > 1:
                for oid in qname[1:]:
                    instance = instance._getattr(oid) # _getattr is used to avoid creating unnecessay nodes.
            return instance 
    except KeyError:
        raise

def get_version(path):
    '''
    Returns version of the tail node on the path.
    '''
    try:
        tail = get(path)
        version = tail._getattr('_version')
        return version
    except KeyError:
        raise

def _collision_check(qname, version):
    '''
    Collision detection

    version comparison  collision
    ------------------- ---------
    latest == proposed     N
    latest != proposed     Y
    latest is None         Y
    '''
    if not version:
        return False
    cont = None
    collision = True
    root_oid = qname[0]
    if root_oid in _idb:
        cont = _idb[root_oid]
    if cont and len(qname) > 1:
        for oid in qname[1:]:
            cont = cont._getattr(oid)
    if cont and cont._version == version:
        collision = False
    return collision

def roots():
    '''
    Lists roots
    '''
    _roots = {} 
    for k,v in _idb.items():
        _roots[k] = v._version
    return _roots 

def old():
    '''
    Lists old roots
    '''
    old_roots = []
    for k,v in _old_roots.items():
        version = [elm[0] for elm in v]
        old_roots.append({k: version})
    return old_roots

def rollback(tega_id, root_oid, backto, subscriber=None, write_log=True):
    '''
    Rollbacks a specific root to a previous version
    '''
    next_version = _idb[root_oid]['_version'] + 1

    roots = _old_roots[root_oid]
    end = len(roots)

    if backto > 0:
        start = backto
    else:
        start = end + backto  # Note: backto is a negative value

    pair = None
    for get in reversed(range(start, end)):
        pair = roots.pop()
    version = pair[0]
    root = pair[1]
    align_vector(root)
    root._setattr('_version', next_version)
    _idb[root_oid] = root
    marker_rollback = '{} {} {}'.format(str(backto), tega_id, root_oid)
    if _log_fd and write_log:
        _log_fd.write(marker_rollback+'\n')
        _log_fd.flush()
        os.fsync(_log_fd)

    log = log_entry(ope=OPE.ROLLBACK.name, path=root_oid, tega_id=tega_id,
            instance=None, backto=backto)
    notify_batch = {}
    for path_, subscriber in channels.items():
        if path_.split('.')[0] == root_oid:
            for s in subscribers:
                notify_batch[s] = [log]
    _notify_broadcast(notify_batch=notify_batch, subscriber=subscriber)

def _timestamp(line):
    '''
    Returns timestamp.
    '''
    return line.lstrip(COMMIT_FINISH_MARKER).rstrip('\n')
    
def reload_log():
    '''
    Reloads log to reorganize a tree in idb
    '''
    PUT = OPE.PUT
    DELETE = OPE.PUT
    SS = OPE.SS

    t = None 
    multi = []

    _log_fd.seek(0)
    for line in _log_fd:
        line = line.rstrip('\n')
        if line.startswith(ROLLBACK_MARKER):
            args = line.split(' ')
            rollback(args[1], args[2], int(args[0]), write_log=False)
        elif line.startswith(COMMIT_FINISH_MARKER) and len(multi) > 0:
            timestamp = _timestamp(line)
            t = tx()
            put = t.put
            delete = t.delete
            for crud in multi:
                ope = crud[0]
                if ope == PUT:
                    instance = crud[1]
                    tega_id = crud[2]
                    put(instance, tega_id=tega_id, deepcopy=False)
                elif ope == DELETE:
                    path = crud[1]
                    tega_id = crud[2]
                    delete(path, tega_id=tega_id)
            t.commit(write_log=False)
            del multi[:]
        elif line.startswith(COMMIT_FINISH_MARKER):
            pass
        elif line.startswith(COMMIT_START_MARKER) or line.startswith(SYNC_CONFIRMED_MARKER):
            pass
        else:
            log = eval(line)
            ope = log['ope']
            path = log['path']
            instance = log['instance']
            tega_id = log['tega_id']
            if ope == PUT.name:
                if path:
                    root = subtree(path, instance)
                else:
                    root = dict2cont(instance)
                multi.append((PUT, root, tega_id))
            elif ope == DELETE.name:
                multi.append((DELETE, path, tega_id))
            elif ope == SS.name:
                root_oid = instance['_oid']
                root = deserialize(instance)
                _idb[root_oid] = root

def loglist_for_sync(root_oid, version):
    '''
    Accumulates log entries until the version.

    log.global.0       log.global.l       log.global.n
    +------------+     +------------+     +------------+ ^
    |            |     |    SS      |     |    SS      | |
    |            |     |------------|     |            | |
    |            |     |            | ^   |            | |
    |            |     |            | |   |            | |
    +------------+     +------------+ |   +------------+ |
    '''
    multi = []
    notifications = []
    if version < 0:
        version = -1
    try:
        version_ = _idb[root_oid]['_version']
    except KeyError:
        return multi
    if version_ <= version:
        return multi 

    max_ = commit_log_number(server_tega_id, _log_dir)

    continue_ = True
    begin = False
    match = False

    while continue_ and max_ >= 0:
        filename = _commit_log_filename(server_tega_id, max_)
        log_file = os.path.join(_log_dir, filename)
        max_ -= 1

        with open(log_file, 'r') as fd:
            g = readline_reverse(fd)
            while True:
                try:
                    line = next(g).rstrip('\n')
                except StopIteration:
                    break

                if line == '':
                    pass
                elif line.startswith(COMMIT_FINISH_MARKER):
                    begin = True
                elif line.startswith(COMMIT_START_MARKER):
                    begin = False
                    if match:
                        version_ -= 1
                        match = False
                        multi.insert(0, notifications)
                        notifications = []
                    if version_ <= version:
                        continue_ = False
                        break
                elif line.startswith(ROLLBACK_MARKER):
                    args = line.split(' ')
                    root_oid_ = args[2]
                    if root_oid_ == root_oid:
                        backto = args[0]
                        tega_id = args[1]
                        log = log_entry(ope=OPE.ROLLBACK.name, path=root_oid,
                                tega_id=tega_id, instance=None,
                                backto=int(backto))
                        if notifications:
                            multi.insert(0, notifications)
                        notifications = [log]
                        multi.insert(0, notifications)
                        notifications = []
                        version_ -= 1
                        if version_ <= version:
                            continue_ = False
                            break
                elif begin:
                    log = eval(line)
                    ope = log['ope']
                    path = log['path']
                    tega_id = log['tega_id']
                    instance = log['instance']
                    if ope == OPE.SS.name:
                        pass
                    elif path.split('.')[0] == root_oid:
                        match = True
                        log = log_entry(ope=ope, path=path, tega_id=tega_id,
                                instance=instance)
                        notifications.insert(0, log)

    return multi 

def crud_batch(notifications, subscriber=None):
    '''
    CRUD operation in a batch.
    '''
    with tx(subscriber=subscriber) as t:
        for crud in notifications:
            ope = crud['ope']
            path = crud['path']
            tega_id = crud['tega_id']
            if ope == OPE.PUT.name:
                instance = subtree(path, crud['instance'])
                t.put(instance, tega_id=tega_id, deepcopy=False)
            elif ope == OPE.DELETE.name:
                t.delete(path, tega_id=tega_id)
            elif ope == OPE.ROLLBACK.name:
                backto = crud['backto']
                rollback(tega_id, path, backto, subscriber=subscriber)

def sync(root_oid, version, subscriber):
    '''
    Leader-Follower synchronization on the root_oid.
    '''
    global _idb
    logging.debug(
            'sync -- root_oid: {}, version: {}'.format(root_oid, version))
    version_ = -1

    if root_oid in _idb:
        version_ = _idb[root_oid]['_version']

    if version_ > version:  # out of sync
        multi = loglist_for_sync(root_oid, version)
        for notifications in multi:
            subscriber.on_notify(notifications)
    else:  # in sync
        pass

def _transactions2notifications(transactions):
    '''
    "notification" is notified by NOTIFY.
    "notifications" is a list of notifications.
    "transactions" is from "sync_db" command.

    notifications: [{ ], ...]
    transactions: [['!', [{ }, ...]], ['+', [{ }, ...]], ...]
    '''
    accumulated = []
    for batch in transactions:
        accumulated.extend(batch[1])
    return accumulated

def save_snapshot(tega_id):
    '''
    Take a snapshot of _idb and saves it to the hard disk.
    '''
    global _log_fd
    _idb_snapshot = {}
    for root_oid in _idb:
        _idb_snapshot[root_oid] = _idb[root_oid].serialize_(internal=True,
                serialize_ephemeral=False)

    num = commit_log_number(server_tega_id, _log_dir)
    filename = _commit_log_filename(server_tega_id, num+1)
    log_file = os.path.join(_log_dir, filename)
    if _log_fd:
        _log_fd.close()
    _log_fd = open(log_file, 'a+')  # append-only file

    finish_marker = COMMIT_FINISH_MARKER+'{}'.format(now())

    _log_fd.write(COMMIT_START_MARKER+'\n')  # commit start
    for root_oid, instance in _idb_snapshot.items():
        log = log_entry(ope=OPE.SS.name, path=root_oid, tega_id=tega_id, instance=instance)
        log = str(log)
        _log_fd.write(log+'\n')
    _log_fd.write(finish_marker+'\n')  # commit finish marker
    _log_fd.flush()
    os.fsync(_log_fd)

def publish(channel, tega_id, message, subscriber):
    '''
    publishes a message to subscribers.
    '''
    subscribers = channels[channel]
    for _subscriber in subscribers:
        if _subscriber != subscriber:
            _subscriber.on_message(channel, tega_id, message)

def rpc(path, args=None, kwargs=None):
    '''
    RPC (Remote Procedure Call).

    Raises KeyError if path is not found in idb.
    '''
    try:
        qname = path2qname(path)
        f = get(path)
        if type(f) == RPC:
            func = get(path)._get_func()
            if args and kwargs:
                return func(*args, **kwargs)
            elif args:
                return func(*args)
            elif kwargs:
                return func(**kwargs)
            else:
                return func()
        else:
            raise NonLocalRPC('path exists but not for local RPC')
    except KeyError:
        raise

@gen.coroutine
def rpc2(path, args=None, kwargs=None, tega_id=None):
    '''
    This method is called by server.py
    '''
    try:
        return rpc(path, args, kwargs)
    except NonLocalRPC:
        if tega_id:
            subscriber = get_subscriber_for_local_db(path)
            try:
                result = yield request(subscriber,
                                       REQUEST_TYPE.RPC,
                                       tega_id=tega_id,
                                       path=path,
                                       args=args,
                                       kwargs=kwargs)
                return result
            except gen.TimeoutError:
                raise
        else:
            raise ValueError('tega_id required for this method')
    except KeyError:
        subscriber = get_subscriber_for_global_db()
        try:
            result = yield request(subscriber,
                                   REQUEST_TYPE.RPC,
                                   tega_id=subscriber.tega_id,
                                   path=path,
                                   args=args,
                                   kwargs=kwargs)
            return result
        except gen.TimeoutError:
            raise

def idb_edges(root_oid=None, old_roots=False):
    '''
    Returns all edges of Cont objects stored in idb
    '''
    all_edges = []

    if root_oid:
        root = _idb[root_oid]
        all_edges.extend([edge for edge in edges(root)])
    else:
        roots = _idb.values()
        for root in roots:
            all_edges.extend([edge for edge in edges(root)])

    if root_oid and old_roots:
        for l in _old_roots[root_oid]:
            all_edges.extend([edge for edge in edges(l[1])])
    elif old_roots:
        for v in _old_roots.values():
            for l in v:
                all_edges.extend([edge for edge in edges(l[1])])

    return all_edges

