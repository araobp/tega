from tega.env import PORT, HEADERS, TRANSACTION_GC_PERIOD, DATA_DIR,\
        WEBSOCKET_PUBSUB_URL, LOGO, CONNECT_RETRY_TIMER,\
        REQUEST_TIMEOUT
import tega.idb
from tega.idb import tx, clear, roots, old, NonLocalRPC
from tega.messaging import build_parser, request, on_response, REQUEST_TYPE
import tega.subscriber
from tega.subscriber import Subscriber, SCOPE
from tega.tree import Cont, is_builtin_type
from tega.util import url2path, subtree

from tornado import gen
import tornado.ioloop
import tornado.web
import tornado.websocket

import argparse
import httplib2
import json
import logging
import socket
import sys
from threading import RLock
import traceback
import time
import urllib
import uuid
import yaml

transactions = {}
tx_lock = RLock()

mhost = None
mport = None
sync_path = None
server_as_subscriber = None

subscriber_clients = {}

plugins = {}

def _tega_id2subscriber(tega_id):
    '''
    Gets tega_id from a REST request param, and returns a subscriber object
    (PubSubHandler instance) registered in subscriber_clients, 
    corresponding to the tega_id.
    '''
    subscriber = None
    if tega_id and tega_id in subscriber_clients:
        subscriber = subscriber_clients[tega_id]
    return subscriber

class WebSocketSubscriber(Subscriber):
    '''
    WebSocket subscriber.
    '''
    def __init__(self, tega_id, scope, tornado_websocket):
        super().__init__(tega_id, scope)
        self.tornado_websocket = tornado_websocket

    def on_notify(self, notifications):
        '''
        Sends NOTIFY to a subscriber

        [idb] -- on_notify(notifications) --> [server] -- NOTIFY -->
        '''
        for d in notifications:
            instance = d['instance']
            if isinstance(instance, Cont):
                d['instance'] = instance.serialize_()  # into JSON format
        self.write_message('NOTIFY\n' + json.dumps(notifications))

    def on_message(self, channel, tega_id, message):
        self.tornado_websocket.write_message('MESSAGE {} {}\n{}'.
                format(channel, tega_id, json.dumps(dict(message=message))))

    def write_message(self, data):
        self.tornado_websocket.write_message(data)

class ManagementRestApiHandler(tornado.web.RequestHandler):
    '''
    REST API for tega-db management
    '''
    def post(self, cmd):
        if cmd == 'clear':
            result = globals()[cmd]()  # commands in tega.idb
            if result:
                self.write(json.dumps(result))
                self.set_header('Content-Type', 'application/json')
        elif cmd == 'rollback':
            root_oid = self.get_argument('root_oid', None)
            backto = self.get_argument('backto', None)
            tega.idb.rollback(root_oid, int(backto))
        elif cmd == 'index':
            path = self.get_argument('path', None)
            tega.idb.create_index(path)
        elif cmd == 'begin':
            tega_id = self.get_argument('tega_id')
            t = tx(subscriber=_tega_id2subscriber(tega_id))
            txid = t.txid
            with tx_lock:
                transactions[txid] = {'tx': t, 'expire': 2}
            data = {'txid': txid}
            self.write(json.dumps(data))
            self.set_header('Content-Type', 'application/json')
        elif cmd == 'cand':
            txid = self.get_argument('txid', None)
            internal = self.get_argument('internal', False)
            if txid:
                with tx_lock:
                    if txid in transactions:
                        t = transactions[txid]['tx']
                        data = t.get_candidate()
                        self.write(json.dumps(data))
                        self.set_header('Content-Type', 'application/json')
                    else:
                        raise tornado.web.HTTPError(404)
            else:
                raise tornado.web.HTTPError(404)

        elif cmd == 'cancel':
            txid = self.get_argument('txid', None)
            with tx_lock:
                if txid in transactions:
                    del transactions[txid]
                else:
                    raise tornado.web.HTTPError(404)
        elif cmd == 'commit':
            txid = self.get_argument('txid', None)
            with tx_lock:
                if txid in transactions:
                    t = transactions[txid]['tx']
                    del transactions[txid]
                    t.commit()
                else:
                    raise tornado.web.HTTPError(404)
        elif cmd == 'sync':
            _sync_request(mhost, mport, sync_path)
        elif cmd == 'ss':
            tega_id = self.get_argument('tega_id', None)
            tega.idb.save_snapshot(tega_id)

    def get(self, cmd):
        if cmd  in ('roots', 'old'):
            result = globals()[cmd]()  # commands in tega.idb
            if result:
                self.write(json.dumps(result))
                self.set_header('Content-Type', 'application/json')
        elif cmd == 'log':
            log_cache = tega.idb.get_log_cache()
            log = json.dumps(tega.idb.get_log_cache())
            self.write(log)
        elif cmd == 'channels':
            channels = tega.idb.get_channels()
            self.write(json.dumps(channels))
            self.set_header('Content-Type', 'application/json')
        elif cmd == 'subscribers':
            subscribers = tega.idb.get_subscribers()
            self.write(json.dumps(subscribers))
            self.set_header('Content-Type', 'application/json')
        elif cmd == 'ids':
            self.write(json.dumps(list(tega.idb.get_tega_ids())))
            self.set_header('Content-Type', 'application/json')
        elif cmd == 'global':
            global_channels = tega.idb.get_global_channels()
            _global_channels = [[k, v.value] for (k, v) in global_channels.items()]
            self.write(json.dumps(_global_channels))
            self.set_header('Content-Type', 'application/json')
        elif cmd == 'forwarders':
            forwarders = tega.idb.get_subscribe_forwarders()
            _forwarders = [v.tega_id for v in forwarders]
            self.write(json.dumps(_forwarders))
            self.set_header('Content-Type', 'application/json')
        elif cmd == 'plugins':
            _plugins = {}
            for k, v in plugins.items():
                _plugins[v.tega_id] = v.scope.value
            self.write(json.dumps(_plugins))
            self.set_header('Content-Type', 'application/json')

class SyncApiHandler(tornado.web.RequestHandler):
    '''
    REST API for tega-db sync operations
    '''
    def post(self, cmd):
        if cmd == 'sync_check':
            sync_path = self.get_argument('sync_path')
            digest = self.get_argument('digest')
            if sync_path and digest:
                synchronized = tega.idb.sync_check(sync_path, digest)
                if not synchronized:
                    raise tornado.web.HTTPError(409)
        elif cmd == 'sync_db':
            sync_path = self.get_argument('sync_path')
            transactions = tornado.escape.json_decode(self.request.body)
            tega_id = self.get_argument('tega_id')
            subscriber = _tega_id2subscriber(tega_id)
            if sync_path and transactions is not None:
                confirmed = tega.idb.get_sync_confirmed(sync_path)
                _transactions = tega.idb.conflict_resolution(subscriber,
                                                             sync_path,
                                                             transactions)
                version = _get_sync_path_version(sync_path)
                sync_ver = 0
                if confirmed:
                    sync_ver = confirmed['sync_ver'] + 1
                tega.idb.sync_confirmed_server(tega_id, sync_path, version, sync_ver)
                self.write(json.dumps(_transactions))
                self.set_header('Content-Type', 'application/json')
            else:
                raise tornado.web.HTTPError(400)

class RestApiHandler(tornado.web.RequestHandler):
    '''
    REST API for tega-db CRUD operations
    '''

    def get(self, id):
        '''
        GET(read) operation
        '''
        version = self.get_argument('version', None)
        internal = self.get_argument('internal', None)
        txid = self.get_argument('txid', None)
        tega_id = self.get_argument('tega_id')
        if version:
            version = int(version)
        if internal:
            internal = True
        else:
            internal = False
        path = url2path(id)
        value = None
        try:
            if txid:
                with tx_lock:
                    if txid in transactions:
                        t = transactions[txid]['tx']
                        value = t.get(path, tega_id=tega_id, version=version)
            else:
                value = tega.idb.get(url2path(id), version=version)
            if isinstance(value, Cont) or is_builtin_type(value):
                self.write(value.dumps_(internal=internal))
            else:
                self.write(json.dumps(value))
            self.set_header('Content-Type', 'application/json')
        except KeyError:
            logging.info('path "{}" not found in global idb'.format(path))
            raise tornado.web.HTTPError(400)

    def put(self, id):
        '''
        PUT(create/update) operation
        '''
        data = tornado.escape.json_decode(self.request.body)
        version = self.get_argument('version', None)
        txid = self.get_argument('txid', None)
        tega_id = self.get_argument('tega_id')
        if version:
            version = int(version)
        path = url2path(id)
        cont = subtree(path, data)
        if txid:
            with tx_lock:
                if txid in transactions:
                    t = transactions[txid]['tx']
                    t.put(cont, tega_id=tega_id, version=version, deepcopy=False)
                else:
                    raise tornado.web.HTTPError(404)
        else:
            with tx(subscriber=_tega_id2subscriber(tega_id)) as t:
                try:
                    t.put(cont, tega_id=tega_id, version=version, deepcopy=False)
                except ValueError as e:
                    raise tornado.web.HTTPError(409)

    def delete(self, id):
        '''
        DELETE operation
        '''
        version = self.get_argument('version', None)
        txid = self.get_argument('txid', None)
        tega_id = self.get_argument('tega_id')
        if version:
            version = int(version)
        path = url2path(id)
        if txid:
            with tx_lock:
                if txid in transactions:
                    t = transactions[txid]['tx']
                    t.delete(path, tega_id=tega_id, version=version)
                else:
                    raise tornado.web.HTTPError(404)
        else:
            tega_id = self.get_argument('tega_id')
            with tx(subscriber=_tega_id2subscriber(tega_id)) as t:
                try:
                    t.delete(path, tega_id=tega_id, version=version)
                except ValueError as e:
                    raise tornado.web.HTTPError(409)

class PubSubHandler(tornado.websocket.WebSocketHandler):
    '''
    Data Change Notification subscription
    '''

    def initialize(self):
        self.parser = build_parser('server')
        self.tega_id = None
        self.subscriber = None

    def check_origin(self, origin):
        '''
        Overrides Tornado's "check_origin" method to disable WebSocket origin check
        '''
        return True

    def open(self, *args):
        '''
        WebSocket open.
        '''
        logging.info('WebSocket(server): connection established with {}'.format(self))

    def on_message(self, msg):
        '''
        Handles SESSION/SUBSCRIBE/UNSUBSCRIBE request from a subscriber.
        '''
        cmd, param, body = self.parser(msg)

        if cmd == 'SESSION':
            self.tega_id = param[0]  # tega ID from a tega client
            scope = SCOPE(param[1])
            self.subscriber = WebSocketSubscriber(self.tega_id, scope, self)
            if scope == SCOPE.GLOBAL:
                def _on_subscribe(path, scope):
                    self.write_message(
                            'SUBSCRIBE {} {}'.format(path, scope.value))
                self.subscriber.on_subscribe = _on_subscribe
                tega.idb.add_subscribe_forwarder(self.subscriber)
            subscriber_clients[self.tega_id] = self.subscriber
            tega.idb.add_tega_id(self.tega_id)
        elif cmd == 'SUBSCRIBE':
            if param:
                channel = param[0]
                scope = SCOPE(param[1])
                tega.idb.subscribe(self.subscriber, channel, scope)
                if scope == SCOPE.SYNC:
                    self.subscriber.on_subscribe(channel, scope)
            else:
                logging.warn('WebSocket(server): no channel indicated in SUBSCRIBE request')
        elif cmd == 'UNSUBSCRIBE':
            if param:
                tega.idb.unsubscribe(self.subscriber, param)
                self.write_message('UNSUBSCRIBE {}'.format(param))
            else:
                tega.idb.unsubscribe_all(self.subscriber)
                self.write_message('UNSUBSCRIBE')
        elif cmd == 'PUBLISH':
            tega.idb.publish(param, self.tega_id, body['message'],
                    self.subscriber)
        elif cmd == 'NOTIFY':
            tega.idb.crud_batch(body, self.subscriber)
        elif cmd == 'MESSAGE':
            channel = param[0]
            tega_id = param[1]
            tega.idb.publish(channel, tega_id, body['message'], self.subscriber)
        elif cmd == 'REQUEST':
            type_ = REQUEST_TYPE(param[1])
            if type_ == REQUEST_TYPE.RPC:
                self._route_rpc_request(param)
        elif cmd == 'RESPONSE':
            type_ = REQUEST_TYPE(param[1])
            if type_ == REQUEST_TYPE.RPC:
                self._route_rpc_response(param, body)

    def _route_rpc_request(self, param):
        seq_no = int(param[0])
        tega_id = param[2]
        qs = param[3]
        qs_dict = urllib.parse.parse_qs(qs, encoding='utf-8')
        path = qs_dict['path'][0]
        dst_tega_id = str(tega.idb.get(path)).lstrip('%').split('.')[0]
        if dst_tega_id in plugins.keys():  # to global idb
            args = eval(qs_dict['args'][0])
            kwargs = eval(qs_dict['kwargs'][0])
            result = tega.idb.rpc(path, args, kwargs)
            if result:   # Returns RESPONSE
                self.write_message('RESPONSE {} {} {}\n{}'.
                        format(seq_no,
                               REQUEST_TYPE.RPC.name,
                               tega_id,
                               json.dumps(result)))
        else:  # Forwards the REQUEST to another local idb
            _subscriber = tega.idb.get_subscriber_instances(dst_tega_id)[0]
            _subscriber.write_message('REQUEST {} {} {} {}'.
                                      format(seq_no,
                                             REQUEST_TYPE.RPC.name,
                                             tega_id,
                                             qs))

    def _route_rpc_response(self, param, body):
        global subscriber_clients
        tega_id = param[2]

        # RESPONSE back to global idb
        if not tega.idb.is_subscribe_forwarder(tega_id):
            on_response(param, body)
        # RESPONSE to be forwarded to local idb
        else:
            seq_no = int(param[0])
            _subscriber = subscriber_clients[tega_id]
            _subscriber.write_message('RESPONSE {} {} {}\n{}'.
                    format(seq_no,
                           REQUEST_TYPE.RPC.name,
                           tega_id,
                           json.dumps(body)))

    def on_close(self):
        '''
        WebSocket close.
        '''
        tega.idb.unsubscribe_all(self.subscriber) 
        for tega_id in list(subscriber_clients.keys()):
            if subscriber_clients[tega_id] == self:
                del subscriber_clients[tega_id]
        tega.idb.remove_tega_id(self.tega_id)
        if self.subscriber and self.subscriber.scope == SCOPE.GLOBAL:
            tega.idb.remove_subscribe_forwarder(self.subscriber)
        logging.info('WebSocket(server): connection closed with {} and all channels unsubscribed'.format(self))

class RpcHandler(tornado.web.RequestHandler):
    '''
    RPC (Remote Procedure Call). 
    '''

    @gen.coroutine
    def post(self):
        tega_id = self.get_argument('tega_id')
        path = self.get_argument('path')
        _args = self.get_argument('args', None)
        _kwargs = self.get_argument('kwargs', None)
        args = kwargs = None
        if _args:
            args = eval(_args)
        if _kwargs:
            kwargs = eval(_kwargs)
        result = yield tega.idb.rpc2(path, args, kwargs, tega_id)
        if result:
            self.write(json.dumps({'result': result}))
            self.set_header('Content-Type', 'application/json')

def transaction_gc():
    '''
    Transaction objects garbage collector
    '''
    with tx_lock:
        for txid in list(transactions.keys()):
            expire = transactions[txid]['expire']
            if expire == 0:
                del transactions[txid]
                print('id: {} expired'.format(txid))
            else:
                transactions[txid]['expire'] = expire - 1

def _get_sync_path_version(sync_path):
    '''
    Gets version of the sync_path.

    Returns -1 if the sync_path is not found in idb.
    '''
    version = -1
    try:
        version = tega.idb.get_version(sync_path) 
    except KeyError:
        logging.info('sync path "{}" not found in local tega db'.format(
            sync_path))
    return version

def _sync_request(mhost, mport, sync_path):
    '''
    Synchronization request from local idb to global idb.

    TODO: initiating sync request from Master to Slave as well.
    '''

    conn = httplib2.Http()

    commiters = tega.idb.commiters(sync_path)
    digest = tega.idb.commiters_hash(commiters)
    url = 'http://{}:{}/_sync_check?sync_path={}&digest={}'.format(
            mhost, mport, sync_path, digest)

    try:
        response, body = conn.request(url, 'POST', None, HEADERS)
    except ConnectionRefusedError:
        raise

    logging.debug('response status: {}'.format(response.status))
    if response.status == 200:  # Already synchronized
        return

    elif response.status == 409:  # Conflict
        tega_id = server_as_subscriber.tega_id
        url = 'http://{}:{}/_sync_db?sync_path={}&tega_id={}'.format(
                mhost, mport, sync_path, tega_id)
        url_confirmed = 'http://{}:{}'.format(mhost, mport)
        confirmed, transactions = tega.idb.transactions_since_last_sync(sync_path)
        logging.debug('transactions since last sync: {}'.format(transactions))
        response, body = conn.request(url, 'POST',
                json.dumps(transactions), HEADERS)
        if response.status == 200:
            _transactions = json.loads(body.decode('utf-8'))
            logging.debug('sync response received - \n{}'.
                    format(yaml.dump(_transactions)))
            tega.idb.conflict_resolution(server_as_subscriber,
                    sync_path, _transactions)
            version = _get_sync_path_version(sync_path)
            sync_ver = 0
            if confirmed:
                sync_ver = confirmed['sync_ver'] + 1
            tega.idb.sync_confirmed(url_confirmed, sync_path, version, sync_ver)
    else:
        # TODO: error condition
        logging.debug('{} {}'.format(response.status, response.reason))
        pass

class _SubscriberClient(object):
    '''
    Subscriber client for server.py itself, for db dync.

    [server.py] <------------------ [server.py]
    subscriber as PubSubHandler     subscriber as _SubscriberClient

    Note: SESSION message is never sent from global idb to local idb.

    '''

    def __init__(self, mhost, mport, sync_path, tega_id):
        self.mhost = mhost
        self.mport = mport
        self.sync_path = sync_path
        self.tega_id = tega_id
        self.client = None
        self.on_notify = None
        self.parser = build_parser('client')
        tega.idb.add_tega_id(tega_id)

    def _build_send_subscribe(self):
        '''
        Sends a SUBSCRIBE message to another tega db.
        '''
        def _send_subscribe(path, scope):
            self.client.write_message('SUBSCRIBE {} {}'.format(path,
                scope.value))
        return _send_subscribe

    @gen.coroutine
    def _connect_to_global_db(self):
        '''
        WebSocket to global idb.
        '''
        while True:
            try:
                # Connects to global idb
                self.client = yield tornado.websocket.websocket_connect(
                        WEBSOCKET_PUBSUB_URL.format(self.mhost, self.mport))

                # Builds send_subscribe function
                self.send_subscribe = self._build_send_subscribe()

                # Sets WebSocketSubscriber to self
                self.subscriber = WebSocketSubscriber(self.tega_id,
                        SCOPE.GLOBAL, self.client)

                # Subscribe forwarder
                def _on_subscribe(path, scope):
                    self.send_subscribe(path, scope)
                self.subscriber.on_subscribe = _on_subscribe
                tega.idb.add_subscribe_forwarder(self.subscriber)

                # Sends SESSION to global idb.
                self.client.write_message('SESSION {} {}'.format(
                                    self.tega_id, SCOPE.GLOBAL.value))

                # Sends SUBSCRIBE sync_path sync to global idb.
                self.send_subscribe(self.sync_path, SCOPE.SYNC)

                # (re-)sends SUBSCRIBE <global channel> <scope>
                # to global idb.
                global_channels = tega.idb.get_global_channels()
                for channel, scope in global_channels.items():
                    self.send_subscribe(channel, scope)

                break
            except socket.error as e:
                logging.warning('global idb does not seem to be running...')
                time.sleep(CONNECT_RETRY_TIMER)
            except Exception as e:
                traceback.print_exc()

    def _process_message(self, msg):
        '''
        Handles a message from global idb.
        '''
        cmd, param, body = self.parser(msg)

        if cmd == 'NOTIFY':
            tega.idb.crud_batch(body, self.subscriber)
        elif cmd == 'MESSAGE':
            channel = param[0]
            tega_id = param[1]
            tega.idb.publish(channel, tega_id,
                    body['message'], self.subscriber)
        elif cmd == 'SUBSCRIBE':
            channel = param[0]
            scope = SCOPE(param[1])  # Ignored
            tega.idb.subscribe(self.subscriber, channel)
        elif cmd == 'UNSUBSCRIBE':
            if param:
                tega.idb.unsubscribe(self.subscriber, param)
            else:
                tega.idb.unsubscribe_all(self.subscriber)
        elif cmd == 'REQUEST':
            seq_no = param[0]
            type_ = param[1]
            tega_id = param[2]
            qs = param[3]
            qs_dict = urllib.parse.parse_qs(qs, encoding='utf-8')
            if REQUEST_TYPE(type_) == REQUEST_TYPE.RPC:
                path = qs_dict['path'][0]
                args = eval(qs_dict['args'][0])
                kwargs = eval(qs_dict['kwargs'][0])
                result = tega.idb.rpc(path, args, kwargs)
                self.client.write_message('RESPONSE {} {} {}\n{}'.
                        format(seq_no,
                               REQUEST_TYPE.RPC.name,
                               tega_id,
                               json.dumps(result)))
        elif cmd == 'RESPONSE':
            on_response(param, body)

    @gen.coroutine
    def subscriber_loop(self):
        '''
        Receives a message from global idb.
        '''
        while True:
            yield self._connect_to_global_db()
            while True:
                try:
                    msg = yield self.client.read_message()
                    #print(msg)
                    if msg:
                        self._process_message(msg)
                    else:
                        tega.idb.unsubscribe_all(self.subscriber)
                        break
                except:
                    traceback.print_exc()
                    tega.idb.unsubscribe_all(self.subscriber)
                    break

def main():

    global mhost, mport, sync_path, server_as_subscriber, plugins

    logging.basicConfig(
            level=logging.DEBUG,
            format='%(levelname)s:%(asctime)s:%(message)s')
    usage = 'usage: %prog [options] file'
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--datadir", help="tega DB data directory",
                        type=str, default=DATA_DIR)
    parser.add_argument("-p", "--port", help="REST API server port", type=int,
                        default=PORT)
    parser.add_argument("-H", "--mhost",
            help="Global idb REST API server host name or IP address", type=str,
            default=None)
    parser.add_argument("-P", "--mport", help="Global idb REST API server port",
                        type=int, default=None)
    parser.add_argument("-S", "--syncpath",
            help="Root path to be synchronized with", type=str, default=None)
    parser.add_argument("-s", "--sync",
            help="Synchronize with global idb at start up",
            action='store_true')
    parser.add_argument("-t", "--tegaid", help="tega ID", type=str,
            default=str(uuid.uuid4()))
    parser.add_argument("-e", "--extensions", help="Directory of tega plugins",             type=str, default=None)

    args = parser.parse_args()
    print(args)

    if args.syncpath:
        role = 'client'
    else:
        role = 'server'
    print('{}\ntega_id: {}, sync: {}\n'.format(LOGO, args.tegaid, role))

    if args.syncpath:
        sync_path = args.syncpath
        if not args.mhost or not args.mport:
            print('All --mhost, --mport and --syncpath options MUST be specified')
            sys.exit(1)
        else:
            mhost = args.mhost
            mport = args.mport

    # idb initialization
    tega.idb.start(args.datadir, args.tegaid)  # idb start

    # Reloads previous logs from tega db file
    logging.info('Reloading log from {}...'.format(args.datadir))
    tega.idb.reload_log()  # reloads tega-db log
    logging.info('Reloading done')

    # Attaches plugins to idb
    if args.extensions:
        _plugins = tega.subscriber.plugins(args.extensions)
        for class_ in _plugins:
            singleton = class_()
            singleton.initialize()
            _tega_id = singleton.tega_id
            plugins[_tega_id] = singleton
            tega.idb.add_tega_id(_tega_id)
            logging.info('plugin attached to idb: {}'.format(singleton.__class__.__name__))

    application = tornado.web.Application([
        (r'/_pubsub', PubSubHandler),
        (r'/_rpc', RpcHandler),
        (r'/_(sync_[a-z]+)', SyncApiHandler),
        (r'/_(.*)', ManagementRestApiHandler),
        (r'(.*)', RestApiHandler)
    ])
    application.listen(args.port)
    try:
        tornado.ioloop.PeriodicCallback(transaction_gc,
                TRANSACTION_GC_PERIOD * 1000).start()
        
        if args.mhost and args.mport and args.syncpath:
            tega_id = args.tegaid
            server_as_subscriber = _SubscriberClient(
                    args.mhost, args.mport, args.syncpath, tega_id)
            if args.sync:
                while (True):
                    try:
                        _sync_request(args.mhost, args.mport, args.syncpath)
                        break
                    except ConnectionRefusedError:
                        print('global idb does not seem to be running...')
                        time.sleep(CONNECT_RETRY_TIMER)
                print('sync confirmed')

            tornado.ioloop.IOLoop.current().run_sync(
                    server_as_subscriber.subscriber_loop)
        else:
            tornado.ioloop.IOLoop.current().start()

    except KeyboardInterrupt:
        tega.idb.stop()  # idb stop
        print('')
        print('see you!')
        sys.exit(0)
