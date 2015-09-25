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

def build_parser(direction):
    '''
    The argument "direction" is for a debugging purpose only.
    '''
    def _parse_msg(msg):
        '''
        tega WebSocket message format

        seq_no                  = 1*DIGIT
        tega_id                 = 1*( ALPHA / DIGIT / "-" / "_" )
        TEGA-websocket-message  = Session / Subscribe / Unsubscribe / Publish /
                                  Notify / Message / Request / Response
        TEGA-scope              = "global" / "local" / "sync"
        Session                 = "SESSION" SP tega_id SP TEGA-scope
        Subscribe               = "SUBSCRIBE" SP path SP TEGA-scope
        Unsubscribe             = "UNSUBSCRIBE" SP path
        Notify                  = "NOTIFY" CRLF notifications
        Publish                 = "PUBLISH" SP channel CRLF message
        Message                 = "MESSAGE" SP channel SP tega_id CRLF message
        Request                 = "REQUEST" SP seq_no SP TEGA-request-type SP
                                   tega_id SP qs
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

@gen.coroutine
def request(subscriber, request_type, tega_id, **kwargs):
    '''
    tega request/response service -- this method returns a generator
    (tornado coroutine) to send a request to a remote tega db.
    '''
    global seq_no
    qs = urllib.parse.urlencode(dict(**kwargs))  # query string
    seq_no += 1
    if seq_no > 65535:  # seq_no region: 0 - 65535.
        seq_no = 0
    subscriber.write_message('REQUEST {} {} {} {}'.format(
        seq_no, request_type.name, tega_id, qs))
    queue = Queue(maxsize=1)  # used like a synchronous queue
    callback[seq_no] = queue  # synchronous queue per request/response
    try:
        result = yield queue.get(timeout=timedelta(seconds=REQUEST_TIMEOUT))
        raise gen.Return(result)  # Py <= 3.2 cannot return data from a generator.
        # return result  # Py => 3.3 can return data from a generator.
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



