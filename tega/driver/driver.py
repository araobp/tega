#!/usr/bin/env python3.4

from tega.env import HOST, PORT, HEADERS, WEBSOCKET_PUBSUB_URL
from tega.idb import OPE
from tega.messaging import build_parser
from tega.subscriber import SCOPE
from tega.tree import Cont
from tega.util import instance2url, path2url, subtree, dict2cont

import httplib2
import json
import tornado
import uuid
import urllib

POST = OPE.POST.name 
PUT = OPE.PUT.name 
GET = OPE.GET.name 
DELETE = OPE.DELETE.name 

def _make_urlencode(base_url):
    def _urlencode(path_, **kwargs):
        _kwargs = {}
        if kwargs:
            for k,v in kwargs.items():
                if v is None or v is False:
                    pass
                else:
                    _kwargs[k] = v
            return base_url+path_+'?'+urllib.parse.urlencode(_kwargs)
        else:
            return base_url+path_
    return _urlencode

class TransactionException(Exception):
    '''
    Transaction exception
    '''
    def __init__(self, *, response=None, message=None):
        response_msg = msg = ''
        if response:
            response_msg = '{} {}'.format(response.status, response.reason)
        if message:
            msg = '\n' + message
        self.message = response_msg + msg

    def __str__(self):
        return self.message

class CRUDException(Exception):
    '''
    CRUD exception
    '''
    def __init__(self, response):
        self.message = '{} {}'.format(response.status, response.reason)

    def __str__(self):
        return self.message

class SubscriptionException(Exception):
    '''
    Subscription exception
    '''

    def __init__(self, response):
        self.message = '{} {}'.format(response.status, response.reason)

    def __str__(self):
        return self.message

class Driver(object):
    '''
    tega-db python driver.

    (1) REST client for CRUD operations
    (2) WebSocket client for pubsub

    This class makes use of tornado's WebSocket.

    NOTE: websockets APIs are different from Tornado's ones..
    '''

    def __init__(self, host=HOST, port=PORT, tega_id=None, subscriber=None):
        '''
        HTTP connection initialization
        '''
        self.conn = httplib2.Http()
        self.base_url = 'http://{}:{}'.format(host, port)
        self.txid = None
        self.pubsub_url = WEBSOCKET_PUBSUB_URL.format(host, port)
        self._tega_id = tega_id 
        self.client = None
        self.parser = build_parser('driver')
        self._urlencode = _make_urlencode(self.base_url)
    
        if subscriber:
            self.subscriber = subscriber
            self._tega_id = subscriber.tega_id
        elif tega_id:
            self._tega_id = tega_id
        else:
            self._tega_id = str(uuid.uuid4())

        for cmd in ('roots', 'old', 'channels', 'subscribers',
                    'ids', 'global', 'forwarders', 'plugins', 'reload'):
            setattr(self, cmd, self._build_cmd(cmd))

    @property
    def tega_id(self):
        return self._tega_id

    def _cmdencode(self, cmd, **kwargs):
        return self._urlencode('/_'+cmd, **kwargs)

    def _build_cmd(self, cmd):
        '''
        Command builder.
        '''
        def _cmd():
            response, body = self.conn.request(self._cmdencode(cmd),
                                               GET, None, HEADERS)
            if body:
                body = json.loads(body.decode('utf-8'))
            return (response.status, response.reason, body)
        return _cmd

    def _mgmt_cmd(self, cmd, **kwargs):
        response, body = self.conn.request(self._cmdencode(cmd, **kwargs),
                                           POST, None, HEADERS)
        if response.status >=300 or response.status < 200:
            raise CRUDException(response=response)
        else:
            return (response, body)

    def clear(self):
        '''
        clear command
        '''
        response, body = self._mgmt_cmd('clear')
        return (response.status, response.reason, None)

    def sync(self):
        '''
        sync command
        '''
        response, body = self._mgmt_cmd('sync')
        if body:
            body = json.loads(body.decode('utf-8'))
        return (response.status, response.reason, body)

    def ss(self):
        '''
        Saves a snapshot
        '''
        response, body = self._mgmt_cmd('ss', tega_id=self.tega_id)
        return (response.status, response.reason, None)

    def edges(self, root_oid=None, old_roots=False):
        '''
        Returns edges of graph data stored in idb
        '''
        response, body = self.conn.request(self._cmdencode('edges',
                                           root_oid=root_oid,
                                           old_roots=old_roots),
                                           GET, None, HEADERS)
        body = json.loads(body.decode('utf-8'))
        return (response.status, response.reason, body)

    def rollback(self, root_oid, backto):
        '''
        rollback command
        '''
        url = self._cmdencode('rollback', tega_id=self.tega_id,
                root_oid=root_oid, backto=backto)
        response, body = self.conn.request(url, POST, None, HEADERS)
        return (response.status, response.reason, None)

    def _response_check(self, response):
        if response.status >= 300 or response.status < 200:
            raise CRUDException(response=response)

    def put(self, instance, version=None, ephemeral=False):
        '''
        CRUD create/update operation
        '''
        url = self._urlencode(instance2url(instance), txid=self.txid,
                             version=version, tega_id=self.tega_id,
                             ephemeral=ephemeral)
        body_json = instance.dumps_()
        response, body = self.conn.request(url, PUT, body_json, HEADERS)
        self._response_check(response)

    def delete(self, path, version=None):
        '''
        CRUD delete operation
        '''
        url = self._urlencode(path2url(path), txid=self.txid,
                             version=version, tega_id=self.tega_id)
        response, body = self.conn.request(url, DELETE, None, HEADERS)
        self._response_check(response)

    def get(self, path, version=None, internal=False, python_dict=False,
            regex_flag=False):
        '''
        CRUD read operation
        '''
        url = self._urlencode(path2url(path), txid=self.txid,
                             version=version, tega_id=self.tega_id,
                             internal=internal, regex_flag=str(regex_flag))

        response, body = self.conn.request(url, GET, None, HEADERS)
        if response.status >= 300 or response.status < 200:
            raise CRUDException(response=response)

        dict_data = json.loads(body.decode('utf-8'))
        if python_dict:
            return dict_data  # Returns Dict
        else:
            if regex_flag:
                return [dict2cont(elm) for elm in dict_data]
            return subtree(path, dict_data)  # Returns Cont

    def begin(self):
        '''
        begin command
        '''
        if not self.txid:
            response, body = self._mgmt_cmd('begin', tega_id=self.tega_id)
            status = response.status
            if status == 200:
                self.txid = json.loads(body.decode('utf-8'))['txid']
                return self.txid 
            else:
                # TODO: rest.py should return different status code for errors
                raise TransactionException(response=response)
        else:
            raise TransactionException(message='id: {} not commited yet!'.format(self.txid))

    def cand(self, internal=False, python_dict=False):
        '''
        Candidate config.
        '''
        if self.txid:
            url = self._cmdencode('cand', txid=self.txid, internal=internal)
            response, body = self.conn.request(url, POST, None, HEADERS)
            status = response.status
            json_data = body.decode('utf-8')
            if python_dict:
                return json.loads(json_data)
            else:
                return dict2cont(json_data)
        else:
            raise TransactionException(message='no ongoing transaction')

    def cancel(self):
        txid = self.txid
        if txid:
            url = self._cmdencode('cancel', txid=txid)
            response, body = self.conn.request(url, POST, None, HEADERS)
            status = response.status
            reason = response.reason
            if status == 200:
                self.txid = None
                return txid
            else:
                raise TransactionException(response=response,
                        message='id: {} expired'.format(txid))
        else:
            raise TransactionException(message='no ongoing transaction')

    def commit(self):
        txid = self.txid
        if txid:
            url = self._cmdencode('commit', txid=txid)
            response, body = self.conn.request(url, POST, None, HEADERS)
            status = response.status
            reason = response.reason
            self.txid = None
            if status == 200:
                return txid 
            else:
                raise TransactionException(response=response,
                        message='id: {} rejected'.format(txid))
        else:
            raise TransactionException('no ongoing transaction')

    def _send(self, cmd, args=None, message=None):
        if self.client:
            if message and _args:
                self.client.write_message('{}\n{}'.
                        format(' '.join(cmd, *_args), message))
            elif _args:
                self.client.write_message(' '.join(cmd, *_args))
            else:
                self.client.write_message(cmd)
        else:
            raise SubscriptionException(message='No subscriber client set')

    def rpc(self, func_path, *args, **kwargs):
        '''
        RPC (Remote Procedure Call)
        '''
        url = None
        body = None

        url = self._cmdencode('rpc', tega_id=self.tega_id, path=func_path)
        if args and kwargs:
            body = json.dumps(dict(args=args, kwargs=kwargs))
        elif args:
            body = json.dumps(dict(args=args))
        elif kwargs:
            body = json.dumps(dict(kwargs=kwargs))

        response, body = self.conn.request(url, POST, body, HEADERS)
        if response.status == 200 and body:
            body = json.loads(body.decode('utf-8'))['result']
            return (response.status, response.reason, body)
        else:
            return (response.status, response.reason, None)

    @tornado.gen.coroutine
    def subscriber_client(self):
        '''
        Receives NOTIFY or MESSAGE from tega REST server.
        '''
        self.client = yield tornado.websocket.websocket_connect(self.pubsub_url)
        if self.subscriber:
            scope = self.subscriber.scope.value
        else:
            scope = SCOPE.LOCAL.value

        self._send(cmd='SESSION', args=[self.tega_id, scope])

        message = yield self.client.read_message()
        cmd, args, body = self.parser(message)
        assert(cmd == 'SESSIONACK')
        self.subscriber.on_init()

        while self.client:
            message = yield self.client.read_message()
            if not message:  # TODO: "WebSocket is disconnected" handler
                break
            cmd, args, body = self.parser(message)
            if cmd == 'NOTIFY':
                self.subscriber.on_notify(body)
            elif cmd == 'MESSAGE':
                channel = args[0]
                tega_id = args[1]
                self.subscriber.on_message(channel, tega_id, body['message'])

    def publish(self, channel, message):
        '''
        Publishes a message to subscribers.
        '''
        self._send(cmd='PUBLISH', args=[channel],
                message=json.dumps(dict(message=message)))

    def subscribe(self, path, scope=SCOPE.LOCAL, regex_flag=False):
        '''
        Sends SUBSCRIBE to tega REST server.
        '''
        self._send(cmd='SUBSCRIBE', args=[path, scope.value, str(regex_flag)])

    def unsubscribe(self, path, regex_flag=False):
        '''
        Sends UNSUBSCRIBE to tega REST server.
        '''
        self._send(cmd='UNSUBSCRIBE', args=[path, str(regex_flag)])

    def unsubscribe_all(self):
        '''
        Sends UNSUBSCRIBE to tega REST server.
        '''
        self._send(cmd='UNSUBSCRIBE')

