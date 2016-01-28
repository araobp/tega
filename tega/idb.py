from tega.subscriber import SCOPE
from tega.messaging import request, REQUEST_TYPE
from tega.tree import Cont, RPC
from tega.util import path2qname, qname2path, dict2cont, subtree, newest_commit_log

import copy
from enum import Enum
import hashlib
import logging
import os
import re
import time
from tornado import gen
import traceback
import uuid
import json 

VERSION = '_version'
COMMIT_START_MARKER = '?'
COMMIT_FINISH_MARKER = '@'
ROLLBACK_MARKER = '-'
SYNC_CONFIRMED_MARKER = '*'

_idb = {}  # in-memory DB
_old_roots = {}  # old roots at every version
_log_dir = None  # Log directory
_log_fd = None  # Log file descriptor
_log_cache = []  # log cache

server_tega_id = None  # Server's tega ID
tega_ids = set()  # tega IDs of subscribers and plugins
channels = {}  # channels subscribed by subscribers
global_channels = {}  # channels belonging to global or sync scope
subscribers = {}  # subscribers subscribing channels
subscribe_forwarders = set()

class OPE(Enum):
    '''
    CRUD operations
    '''
    POST = 1
    GET = 2
    PUT = 3
    DELETE = 4 

class POLICY(Enum):
    '''
    Conflict resolution policy
    '''
    WIN = '+'
    LOOSE = '-'
    RAISE_EXCEPTION = '!'

class NonLocalRPC(Exception):
    '''
    "Non-local RPC called" exception.
    '''

    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return self.reason

def start(data_dir, tega_id):
    '''
    Starts tega db
    '''
    global _log_fd
    global _log_dir
    global server_tega_id
    server_tega_id = tega_id
    _log_dir = os.path.join(os.path.expanduser(data_dir))
    seq_no = newest_commit_log(server_tega_id, _log_dir)
    log_file_name = 'log.{}.{}'.format(server_tega_id, seq_no)
    log_file = os.path.join(_log_dir, log_file_name)
    _log_fd = open(log_file, 'a+')  # append-only file

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
    global _idb, _old_roots, _log_cache
    _log_fd.seek(0)
    _log_fd.truncate()
    _idb = {}
    _old_roots = {}
    _log_cache = []

def subscribe(subscriber, path, scope=SCOPE.LOCAL):
    '''
    subscribes a path as a channel
    '''
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
    if scope == SCOPE.GLOBAL or scope == SCOPE.SYNC:
        global_channels[path] = scope
        if not subscriber in subscribe_forwarders:  # Not from a forwarder.
            for _subscriber in subscribe_forwarders:
                if subscriber != _subscriber:
                    _subscriber.on_subscribe(path, scope)

def unsubscribe(subscriber, path):
    '''
    unsubscribes a path as a channel
    '''
    if path in channels:
        channels[path].remove(subscriber)
        if not channels[path]:
            del channels[path]
            if path in global_channels[path]:
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
            unsubscribe(subscriber, channel)
    else:
        logging.warn('{} not subscribing any channels'.format(subscriber))

def add_tega_id(tega_id):
    tega_ids.add(tega_id)

def remove_tega_id(tega_id):
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

def log_entry(ope, path, tega_id, instance):
    '''
    Log entry
    '''
    return dict(ope=ope, path=path, tega_id=tega_id, instance=instance)

class tx:
    '''
    tega-db transaction 
    '''

    def __init__(self, tega_id=None, subscriber=None, policy=POLICY.RAISE_EXCEPTION):
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
        self.policy = policy

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
        if isinstance(instance, Cont):
            for k,v in instance.items():
                if type(k) == str and not k.startswith('_'):
                    if isinstance(v, Cont):
                        self._instance_version_set(v, version)
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
        target = _idb
        new_root = None
        tail = None
        root = None
        go = False
        no_copy = False
        prev_version = -1
        new_version = 0
        root_oid = qname[0]

        if root_oid in self.candidate:  # copy already exists
            prev_version, new_version, root = self.candidate[root_oid]
            new_root = root
            go = True
            no_copy = True  # operations performed on the copy
        elif not root_oid in target:  # the root does not exist in _idb  
            new_root = Cont(root_oid)
        else:  # the root exists in _idb but its copy is not in self.candidate
            root = target[root_oid]
            prev_version = root._getattr(VERSION)
            new_version = prev_version + 1
            new_root = root.copy_(freeze=True)
            go = True

        target = root
        tail = new_root
        
        if above_tail:
            qname = qname[:-1]

        if len(qname) == 0:
            new_root = tail = None
        else:
            for iid in qname[1:]:
                parent = tail
                if go and iid in target:
                    target = target._extend(iid)
                    if no_copy:
                        tail = target
                    else:
                        tail = target.copy_(freeze=True)
                    tail._setattr('_parent', parent)
                    parent._setattr(VERSION, new_version)
                    parent._setattr(iid, tail)
                else:
                    go = False
                    tail = parent._extend(iid)
                    parent._setattr(VERSION, new_version)

            tail._setattr(VERSION, new_version)
            
        return (prev_version, new_version, new_root, tail)

    def commit(self, write_log=True):
        '''
        Transaction commit

        Note: since this data base is based on Tornado/coroutine,
        this commit function never interrupted by another process or thread.
        '''
        for crud in self.crud_queue:
            func = crud[0]
            if func:  # put() or delete()
                crud[0](*crud[1:])
            else:  # get()
                qname = crud[1]
                tega_id = crud[2]
                self._enqueue_commit(OPE.GET, qname, tega_id, None)

        if len(self.commit_queue) > 0:
            finish_marker = COMMIT_FINISH_MARKER+'{}:{}'.format(time.time(),
                                                          self.policy.value)
            _log_cache.append(COMMIT_START_MARKER)
            if write_log:  # Writes log
                if _log_fd:
                    _log_fd.write(COMMIT_START_MARKER+'\n')  # commit start
                    for log in self.commit_queue:
                        log = str(log)
                        _log_fd.write(log+'\n')
                    _log_fd.write(finish_marker+'\n')  # commit finish marker
                    _log_fd.flush()
                    os.fsync(_log_fd)

            # log cache update
            _log_cache.extend(self.commit_queue)
            _log_cache.append(finish_marker)

        # old roots cache update
        for root_oid in self.candidate:
            prev_version, new_version, new_root = self.candidate[root_oid]
            old_root = None
            if root_oid in _idb:
                old_root = _idb[root_oid]
            if new_root:
                _idb[root_oid] = new_root
            else:
                del _idb[root_oid]
            if old_root:
                if not root_oid in _old_roots:
                    _old_roots[root_oid] = []
                _old_roots[root_oid].append((prev_version, old_root))

        # Notifies the commited transaction to subscribers
        for log in self.commit_queue:
            self._notify_append(log)
        self._notify_commit(self.subscriber)

    def _enqueue_commit(self, ope, qname, tega_id, instance):
        '''
        Appends CRUD to the commit queue.
        '''
        if not tega_id:  # CRUD by a subscriber of this server
            tega_id = self.tega_id
        else:
            pass  # CRUD initiated by a notification or a tega db driver.
        path = qname2path(qname)

        if instance and isinstance(instance, Cont):
            instance = instance.serialize_()

        self.commit_queue.append(log_entry(ope=ope.name, path=path, tega_id=tega_id,
                                 instance=instance))

    def get(self, path, version=None, tega_id=None):
        '''
        GET operation.
        
        By performing GET operation in a transaction, dependency graph
        including GET, PUT and DELETE can be organized. The graph is
        represented as a log.

        '''
        qname = path2qname(path)
        try:
            value = get(path, version)
            #version = value['_version']
            self.crud_queue.append((None, qname, tega_id))
            return value
        except KeyError:
            logging.debug('GET failed with the non-existent path: {}'.format(path))
            raise

    def put(self, instance, tega_id=None, version=None, deepcopy=True, path=None):
        '''
        PUT operation.

        Set "version" to the one from GET operation, when collision check is
        required.
        '''
        if isinstance(instance, dict):
            instance = subtree(path, instance)
        self.crud_queue.append((self._put, instance, tega_id, version, deepcopy))

    def _put(self, instance, tega_id=None, version=None, deepcopy=True):

        if deepcopy:
            if isinstance(instance, Cont):
                instance = instance.deepcopy_()
                instance.freeze_()
            else:  # wrapped built-in types such as wrapped_int
                instance = instance.deepcopy_()
        elif isinstance(instance, Cont):
            instance.freeze_()
        if version and _collision_check(instance.qname_(), version):
            raise ValueError('collision detected')
        else:
            qname = instance.qname_()
            root_oid = qname[0]

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
            prev_version, new_version, new_root, above_tail = self._copy_on_write(qname, above_tail=True)
            self._instance_version_set(instance, new_version)
            if above_tail:
                instance.change_(above_tail)
            else:
                new_root = instance
            if not root_oid in self.candidate:
                self.candidate[root_oid] = (prev_version, new_version, new_root)

            # Commit queue
            if isinstance(instance, Cont):
                instance = instance.deepcopy_()
            self._enqueue_commit(OPE.PUT, qname, tega_id, instance)

    def delete(self, path, tega_id=None, version=None):
        '''
        DELETE operation.

        "path" can be either an instance of Cont or string.
        '''
        self.crud_queue.append((self._delete, path, tega_id, version))

    def _delete(self, path, tega_id=None, version=None):

        qname = None
        if isinstance(path, Cont):
            qname = path.qname_()
        else:
            qname = path2qname(path)
        root_oid = qname[0]

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
            prev_version, new_version, new_root, above_tail = self._copy_on_write(qname, above_tail=True)
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
                self.candidate[root_oid] = (prev_version,
                                            new_version, new_root)

            # Commit queue
            self._enqueue_commit(OPE.DELETE, qname, tega_id, instance)

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

        path_dot = path + '.'  # a.b.c
        qname = path2qname(path)

        # Searches "path" in "channels".
        # Search order: a.b.c, a.b, a (reversed)
        for i in reversed(range(len(qname))):
            #_path = '.'.join(qname[:i+1])
            _path = qname2path(qname[:i+1])
            if _path in channels:
                for subscriber in channels[_path]:
                    try:
                        if not subscriber in self.notify_batch:
                            self.notify_batch[subscriber] = []
                        self.notify_batch[subscriber].append(log)
                    except:
                        traceback.print_exc()
                        logging.warn('subscriber removed - {}'.
                                format(subscriber))
                        channels[_path].remove(subscriber)

        # Searches a child node of the path
        for _path in channels.keys():
            if _path.startswith(path_dot):  #(a.b.c.) matches a.b.c.d.e
                subpath = re.sub(path_dot, '', _path)  #(a.b.c)d.e => d.e
                qname = path2qname(subpath)  #[d, e]
                path_extended = path  #a.b.c
                for oid in qname:
                    if oid in instance:
                        instance = instance[oid]
                        path_extended += '.' + oid
                    else:
                        instance = None
                        break
                if instance:
                    for subscriber in channels[_path]:
                        if not subscriber in self.notify_batch:
                                self.notify_batch[subscriber] = []
                        log['path'] = path_extended
                        log['instance'] = instance

                        self.notify_batch[subscriber].append(log)

    def _notify_commit(self, subscriber=None):
        '''
        Notifies CRUD operations in a batch to subscribers
        '''
        for _subscriber, notifications in self.notify_batch.items():
            if subscriber != _subscriber:
                _subscriber.on_notify(notifications)

        self.notify_batch = {}

def get(path, version=None):
    '''
    GET operation.

    Raises KeyError if path is not found in idb.
    '''
    try:
        qname = path2qname(path)
        tail = None
        root_oid = qname[0]
        root = _idb[root_oid]
        highest = root._version
        if version is None or version == highest:
            tail = root
        else:
            if version < 0:
                version = highest + version
            for tup in _old_roots[root_oid]:
                if tup[0] == version:
                    tail = tup[1]
        if tail:
            if len(qname) > 1:
                for iid in qname[1:]:
                    tail = tail._getattr(iid) # _getattr is used to avoid creating unnecessay nodes.
        return tail
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
        versions = [version[0] for version in v]
        old_roots.append({k: versions})
    return old_roots

def rollback(root_oid, backto, write_log=True):
    '''
    Rollbacks a specific root to a previous version
    '''
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
    _idb[root_oid] = root
    marker_rollback = '{} {}'.format(str(backto), root_oid)
    if _log_fd and write_log:
        _log_fd.write(marker_rollback+'\n')
        _log_fd.flush()
        os.fsync(_log_fd)
    _log_cache.append(marker_rollback)

def create_index(path):
    '''
    Creates an index
    '''
    global _old_roots
    prev_version = -1
    qname = path2qname(path)
    if len(qname) <= 1 or path in _old_roots:
        raise ValueError

    root_oid = qname[0]
    for version, root in _old_roots[root_oid]:
        _iter = iter(qname[1:])
        while True:
            try:
                oid = next(_iter)
                if oid in root:
                    root = root[oid]
                else:
                    break
            except StopIteration:
                version = root._version
                if version == prev_version:
                    prev_version = version
                    break
                else:
                    prev_version = version
                if path not in _old_roots:
                    _old_roots[path] = [(version, root)]
                else:
                    _old_roots[path].append((version, root))
                break

def _timestamp_policy(line):
    '''
    Returns timestamp and policy.
    '''
    timestamp_policy = line.lstrip(COMMIT_FINISH_MARKER).rstrip('\n').split(':')
    timestamp = timestamp_policy[0]
    policy = timestamp_policy[1]
    return (timestamp, policy)
    
def reload_log():
    '''
    Reloads log to reorganize a tree in idb
    '''
    t = None 
    multi = []

    _log_fd.seek(0)
    for line in _log_fd:
        line = line.rstrip('\n')
        if line.startswith(ROLLBACK_MARKER):
            args = line.split(' ')
            rollback(args[1], int(args[0]), write_log=False)
        elif line.startswith(COMMIT_FINISH_MARKER) and len(multi) > 0:
            timestamp, policy = _timestamp_policy(line)
            t = tx(policy=POLICY(policy))
            for crud in multi:
                ope = crud[0]
                if ope == OPE.PUT:
                    instance = crud[1]
                    tega_id = crud[2]
                    t.put(instance, tega_id=tega_id, deepcopy=False)
                elif ope == OPE.DELETE:
                    path = crud[1]
                    tega_id = crud[2]
                    t.delete(path, tega_id=tega_id)
                elif ope == OPE.GET:
                    pass
            t.commit(write_log=False)
            del multi[:]
        elif line.startswith(COMMIT_START_MARKER) or line.startswith(SYNC_CONFIRMED_MARKER):
            _log_cache.append(line)
        else:
            log = eval(line)
            ope = log['ope']
            path = log['path']
            instance = log['instance']
            tega_id = log['tega_id']
            if ope == OPE.PUT.name:
                if path:
                    root = subtree(path, instance)
                else:
                    root = dict2cont(instance)
                multi.append((OPE.PUT, root, tega_id))
            elif ope == OPE.DELETE.name:
                multi.append((OPE.DELETE, path, tega_id))
            elif ope == OPE.GET.name:
                multi.append((OPE.GET,))

def crud_batch(notifications, subscriber=None):
    '''
    CRUD operation in a batch.
    '''
    with tx(subscriber=subscriber) as t:
        for crud in notifications:
            ope = crud['ope']
            path = crud['path']
            instance = subtree(path, crud['instance'])
            tega_id = crud['tega_id']
            if ope == 'PUT':
                t.put(instance, tega_id=tega_id, deepcopy=False)
            elif ope == 'DELETE':
                t.delete(path2qname(path), tega_id=tega_id)

def sync_check(sync_path, digest):
    '''
    Checks if global idb and local idb are synchronized.
    '''
    _commiters = commiters(sync_path)
    _digest = commiters_hash(_commiters)
    logging.debug(
            'sync_check\n digest: {}\n _commiters: {}\n _digest: {}'.
            format(digest, _commiters, _digest))
    if digest == _digest:
        return True
    else:
        return False

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

def conflict_resolution(subscriber, sync_path, transactions):
    '''
    Compares pending transactions between global idb and local idb, then
    detects and filters out collisions.

    This method raises ValueError and terminates abruptly when detected
    collisions cannot be resolved because of conflicting policies between
    global idb and local idb.
    '''
    logging.debug('conflict resolution -\n sync_path: {}\n transactions: {}'.
            format(sync_path, transactions))

    # Pending transactions at Client 
    transactions = _transactions_within_scope(sync_path, transactions)
    # Pending transactions at Server 
    confirmed, _transactions = transactions_since_last_sync(sync_path)
    _transactions = _transactions_within_scope(sync_path, _transactions)

    # Transactions to be filtered out
    _t_remove = set()
    t_remove = set()

    # Detects conflicts and filters out collisions.
    for _t in _transactions:  # each transaction at Server
        _p = [_l['path'] for _l in _t[1]]  # each log in notifications
        _P = set(_p)  # union of paths
        for t in transactions:  # each transaction at Client
            p = [l['path'] for l in t[1]]  # each log in notifications
            P = set(p)  # union of paths
            _tp = _t[0]  # policy at Server
            tp = t[0]  # policy at Client

            if len(_P&P) == 0:  # intersection is null: no collisions detected
                # _t and t pass
                pass
            elif _tp == POLICY.RAISE_EXCEPTION:
                raise ValueError()
            elif tp == POLICY.RAISE_EXCEPTION:
                raise ValueError()
            elif _tp == POLICY.WIN and tp == POLICY.LOOSE:
                # _t passes
                t_remove.add(t)
            elif _tp == POLICY.LOOSE and tp == POLICY.WIN:
                # t passes
                _t_remove.add(_t)
            elif _tp == POLICY.LOOSE and tp == POLICY.LOOSE:
                t_remove.add(t)
                _t_remove.add(_t)

    # Conflict resolution by rolling back to a previous version and commit
    # the filtered transactions again.
    if len(_t_remove) > 0:
        for _t in copy.copy(_transactions):
            if _t in _t_remove:
                _transactions.remove(_t)
        root_oid = sync_path.split('.')[0]
        version = _get_last_sync_marker()['version']
        rollback(root_oid, version, write_log=True)
        _notifications = _transactions2notifications(_transactions)
        crud_batch(_notifications, subscriber=subscriber)
    if (len(t_remove)) > 0:
        for t in copy.copy(transactions):
            if t in t_remove:
                transactions.remove(t)
    notifications = _transactions2notifications(transactions)
    crud_batch(notifications, subscriber=subscriber)

    return _transactions

def get_log_cache():
    '''
    Returns log cache
    '''
    return _log_cache

def sync_confirmed(url, sync_path, version, sync_ver):
    '''
    Writes "sync confirmed" record on tega DB
    '''
    confirmed = dict(url=url, sync_path=sync_path, version=version, sync_ver=sync_ver)
    marker_confirmed = '{}{}'.format(SYNC_CONFIRMED_MARKER, confirmed)
    _log_fd.write(marker_confirmed+'\n')
    _log_fd.flush()
    os.fsync(_log_fd)
    _log_cache.append(marker_confirmed)
    logging.debug('sync confirmed - \n{}\n'.format(json.dumps(marker_confirmed)))

def sync_confirmed_server(tega_id, sync_path, version, sync_ver):
    '''
    Writes "sync confirmed" record on tega DB
    '''
    confirmed = dict(tega_id=tega_id, sync_path=sync_path, version=version, sync_ver=sync_ver)
    marker_confirmed = '{}{}'.format(SYNC_CONFIRMED_MARKER, confirmed)
    _log_fd.write(marker_confirmed+'\n')
    _log_fd.flush()
    os.fsync(_log_fd)
    _log_cache.append(marker_confirmed)
    logging.debug('sync confirmed - \n{}\n'.format(json.dumps(marker_confirmed)))

def save_snapshot(tega_id):
    '''
    Take a snapshot of _idb and saves it to the hard disk.
    '''
    seq_no = newest_commit_log(server_tega_id, _log_dir) + 1  # Increments the log seq number
    _idb_snapshot = {}
    for root_oid in _idb:
        _idb_snapshot[root_oid] = _idb[root_oid].serialize_(internal=True)

    log_file_name = 'log.{}.{}'.format(server_tega_id, seq_no)
    log_file = os.path.join(_log_dir, log_file_name)
    _log_fd = open(log_file, 'a+')  # append-only file

    finish_marker = COMMIT_FINISH_MARKER+'{}:{}'.format(time.time(), POLICY.RAISE_EXCEPTION.value)  # TODO: is raise_exception OK?

    _log_fd.write(COMMIT_START_MARKER+'\n')  # commit start
    for root_oid, instance in _idb_snapshot.items():
        log = log_entry(ope=OPE.PUT.name, path=root_oid, tega_id=tega_id, instance=instance)
        log = str(log)
        _log_fd.write(log+'\n')
    _log_fd.write(finish_marker+'\n')  # commit finish marker
    _log_fd.flush()
    os.fsync(_log_fd)

def _build_scope_matcher(sync_path):
    '''
    Returns sync_path scope matcher.
    '''
    pattern = re.compile('^'+sync_path+'$|^'+sync_path+'\.')

    def match(path):
        path_dot = path + '.'
        if pattern.match(path) or sync_path.startswith(path_dot):
            return True
        else:
            return False

    return match

def _index_last_sync(sync_path=None):
    '''
    _log_cache
    -------------- index
    sync_confirmed   0
    record           1 <== _index_last_sync()
    record           2
    --------------
    '''
    index = -1
    confirmed = None
    len_ = len(_log_cache) 
    if len_ > 0:
        index = len_ - 1
        for record in reversed(_log_cache):
            if type(record) == str and record.startswith(SYNC_CONFIRMED_MARKER):
                confirmed = eval(record.lstrip(SYNC_CONFIRMED_MARKER))
                if sync_path:
                    if confirmed['sync_path'] == sync_path:
                        break
                    else:
                        pass
                else:
                    break
            elif index == 0:
                break
            index -= 1
    return (confirmed, index)

def get_sync_confirmed(sync_path):
    '''
    Returns a sync confirmed marker since last sync.
    '''
    confirmed, index = _index_last_sync(sync_path)
    return confirmed

def _get_last_sync_marker(sync_path=None):
    '''
    _log_cache
    -------------- index
    sync_confirmed   0 <== _get_last_sync_marker()
    record           1
    record           2
    --------------
    '''
    len_ = len(_log_cache)
    if len_ > 0:
        for record in reversed(_log_cache):
            if type(record) == str and record.startswith(SYNC_CONFIRMED_MARKER):
                confirmed = eval(record.lstrip(SYNC_CONFIRMED_MARKER))
                if sync_path:
                    if confirmed['sync_path'] == sync_path:
                        return confirmed
                    else:
                        pass
                else:
                    return confirmed
    return None 

def _gen_transaction_since_last_sync(index):
    '''
    Returns a Python generator to yield a list of log per transaction.
    '''
    if index < 0:
        yield None
    else:
        _tx = []
        for record in _log_cache[index:]:
            if type(record) == dict:
                _tx.append(record)
            elif record.startswith(COMMIT_FINISH_MARKER):
                timestamp, policy = _timestamp_policy(record)
                yield [policy, _tx] 
                _tx = []
            else:
                pass

def _transactions_within_scope(sync_path, transactions):
    '''
    Removes transactions out of scope.
    '''
    match = _build_scope_matcher(sync_path)
    notifications = []
    trans = []
    for transaction in transactions:
        for notification in transaction[1]:
            if match(notification['path']):
                notifications.append(notification)
        if (len(notifications) != 0):
            trans.append([transaction[0], notifications])
            notifications = []
    return trans

def transactions_since_last_sync(sync_path=None):
    '''
    Returns a list of transactions since last sync in the form of:
    [[transaction], [transaction],...]

    TODO: multiple sync_path support.
    '''
    transactions = []
    confirmed, index = _index_last_sync(sync_path)
    for _policy_tx in _gen_transaction_since_last_sync(index):
        if _policy_tx:
            transactions.append(_policy_tx)
        else:
            break
    return (confirmed, transactions)

def _gen_log_cache_since_last_sync(index):
    '''
    _log_cache
    -------------- index
    sync_confirmed   0
    record           1 <== _index_last_sync()
    record           2
    --------------
    yield _log_cache[1], and then _log_cache[2].

    Note: this function returns a Python generator to yield CRUD operations.

    '''
    if index < 0:
        yield None
    else: 
        for record in _log_cache[index:]:
            if type(record) == dict:
                yield record

def commiters(sync_path, version_since=-1):
    '''
    Returns a list of commiters since last sync on the sync_path
    in reversed order, for conflict detection.

    '''
    commiters = []

    match = _build_scope_matcher(sync_path)

    confirmed, index = _index_last_sync(sync_path)
    for crud in _gen_log_cache_since_last_sync(index):
        if crud:
            _path = crud['path']
            _path_dot = _path + '.'

            if match(_path):
                commiters.append(crud['tega_id'])
        else:
            break
    return commiters 

def commiters_hash(commiters):
    '''
    Returns a digest(sha256) of a list of commiters.
    '''
    hash_list = [hashlib.sha256(tega_id.encode('utf-8')).hexdigest() for tega_id in commiters]

    digest_concat = ''
    for digest in hash_list:
        digest_concat += digest
    return hashlib.sha256(digest_concat.encode('utf-8')).hexdigest()

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
        raise gen.Return(rpc(path, args, kwargs))
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
                raise gen.Return(result)
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
            raise gen.Return(result)
        except gen.TimeoutError:
            raise

