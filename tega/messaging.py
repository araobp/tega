from tega.env import REQUEST_TIMEOUT

from datetime import timedelta
from enum import Enum
import json
import logging
import urllib
from tornado import gen
from tornado.queues import Queue

seq_no = 0
callback = {}

class REQUEST_TYPE(Enum):
    RPC = 'RPC'
    SYNC = 'SYNC'
    REFER = 'REFER'

def build_parser(direction):
    '''
    The argument "direction" is for a debugging purpose only.
    '''
    def _parse_msg(msg):
        '''
        tega WebSocket message format

        seq_no                  = 1*DIGIT
        backto                  = 1*DIGIT
        tega_id                 = 1*( ALPHA / DIGIT / "-" / "_" )
        regex_flag              = "True" / "False"
        TEGA-websocket-message  = Session / SessionAck / Subscribe /
                                  Unsubscribe / Publish / Notify / Message /
                                  Request / Response
        TEGA-scope              = "global" / "local"
        Session                 = "SESSION" SP tega_id SP TEGA-scope
        SessionAck              = "SESSIONACK" SP tega_id
        Subscribe               = "SUBSCRIBE" SP path SP TEGA-scope SP regex_flag
        Unsubscribe             = "UNSUBSCRIBE" SP path SP regex_flag
        Notify                  = "NOTIFY" CRLF notifications
        Publish                 = "PUBLISH" SP channel CRLF message
        Message                 = "MESSAGE" SP channel SP tega_id CRLF message
        Roolback                = "ROLLBACK" SP path SP backto
        Request                 = "REQUEST" SP seq_no SP TEGA-request-type SP
                                   tega_id SP path CRLF body 
        Response                = "RESPONSE" SP seq_no SP TEGA-request-type SP
                                   tega_id CRLF body 
        '''
        logging.debug('WebSocket({}): message received - \n{}'.
                format(direction, msg))
        msg = msg.split('\n')
        command_line = msg[0].split(' ')
        cmd = command_line[0]
        params = None
        if len(command_line) == 2:
            params = command_line[1]
        elif len(command_line) > 2:
            params = command_line[1:]
        body = None
        if len(msg) > 1:
            body = json.loads(msg[1])
        return (cmd, params, body)

    return _parse_msg

def parse_rpc_body(body):
    '''
    Parses RPC body
    '''
    args = kwargs = None
    if 'args' in body:
        args = body['args']
    if 'kwargs' in body:
        kwargs = body['kwargs']
    return (args, kwargs)

@gen.coroutine
def request(subscriber, request_type, tega_id, path, **kwargs):
    '''
    tega request/response service -- this method returns a generator
    (tornado coroutine) to send a request to a remote tega db.
    '''
    global seq_no
    seq_no += 1
    if seq_no > 65535:  # seq_no region: 0 - 65535.
        seq_no = 0
    subscriber.write_message('REQUEST {} {} {} {}\n{}'.format(
        seq_no, request_type.name, tega_id, path, json.dumps(kwargs)))
    queue = Queue(maxsize=1)  # used like a synchronous queue
    callback[seq_no] = queue  # synchronous queue per request/response
    try:
        result = yield queue.get(timeout=timedelta(seconds=REQUEST_TIMEOUT))
        return result
    except gen.TimeoutError:
        raise

def on_response(params, body):
    '''
    tega request/response service -- this method is to resume the request
    method.
    '''
    global callback
    seq_no = int(params[0])
    queue = callback.pop(seq_no)
    queue.put(body)



