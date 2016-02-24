from tega.driver import Driver, CRUDException, TransactionException
from tega.env import HOST, PORT, HEADERS, WEBSOCKET_PUBSUB_URL,\
HISTORY_FILE, HISTORY_LENGTH
from tega.idb import OPE
from tega.subscriber import Subscriber, SCOPE
from tega.util import path2url, subtree, func_args_kwargs

import argparse
import httplib2
import io
import json
import os
import pydoc
import re
import readline
import sys
import tornado.websocket
import uuid
import yaml

readline.parse_and_bind('tab: complete')
readline.parse_and_bind('set editing-mode vi')
readline.set_history_length(HISTORY_LENGTH)

operations = '|'.join(['get', 'geta', 'put', 'pute', 'del', 
    'begin', 'cancel', 'commit', 'sub', 'subr',
    'unsub', 'unsubr', 'pub'])
cmd_pattern = re.compile('^(' + operations +
        r')\s+([\(\)\[\]=\-,\.\w\*\\]+)\s*(-*\d*)$|^(rollback)\s+([\w\-]+)\s+(-\d*)$')
rpc_pattern = re.compile('^[\.\w]+\([\w\s\'\"\,\.\/=-]*\)$')
methods = {'get': OPE.GET.name, 'geta': OPE.GET.name,
    'put': OPE.PUT.name, 'del': OPE.DELETE.name}
HELP = '''
[Database management] (M)andatory, (O)ptional
command    root version explanation
---------- ---- ------- -----------------------------------------------------
h                       show this help
q                       quit
id                      show tega ID of this CLI
clear                   empty the database
roots                   list root object IDs
old                     list old root object IDs
sync                    synchronize with global idb 
rollback    M     M     rollback a specific root to a previous version
ss                      take a snapshot
plugins                 show plugins attached to the tega db

[CRUD operations] (M)andatory, (O)ptional, (X) -s option required
command    path version -s  explanation
---------- ---- ------- --- -------------------------------------------------
put         M     O         CRUD create/update operation
pute        M     O      X  CRUD create/update operation (ephemeral node)
get         M     O         CRUD read operation
geta        M     O         CRUD read operation with internal attributes
del         M     O         CRUD delete operation
begin                       begin a transaction
cand                        show a candidate config (not implemented yet)
cancel                      cancel a transaction
commit                      commit a transaction

[PubSub] (M)andatory, (O)ptional, (X) -s option required
command    path version -s  explanation
---------- ---- ------- --- -------------------------------------------------
sub         M            X  subscribe a path as a pubsub channel
subr        M            X  subscribe a regex path as a pubsub channel
unsub       M            X  unsubscribe a path as a pubsub channel
unsubr      M            X  unsubscribe a regex path as a pubsub channel
pub         M            X  publish a message to subscribers
ids                         show all tega IDs of plugins and drivers
channels                    show channels
global                      show global channels (global or sync)
subscribers                 show subscribers
forwarders                  show subscribe forwarders

"unsub *" to subscribe all channels

[RPC]
For example, type a command like this:
a.b.x(1,name='Alice')

'''

driver = None

seq = 0
def prompt():
    '''
    Prints prompt.
    '''
    global seq
    sys.stdout.write('[tega: {}] '.format(seq))
    seq += 1
    sys.stdout.flush()

def gen_prompt():
    '''
    Generates a prompt string.
    '''
    global seq
    while True:
        yield '[tega: {}] '.format(seq)
        seq += 1
        
gen_prompt_ = gen_prompt()

def process_cmd(tornado_loop=False):

    global base_url, conn, txid
    if tornado_loop:
        cmd = sys.stdin.readline().rstrip('\n') 
    else:
        cmd = input(next(gen_prompt_)).strip('\t')
    if cmd == '':
        pass 
    elif cmd == 'h':
        pydoc.pager(HELP)
    elif cmd == 'q':
        readline.write_history_file(HISTORY_FILE)
        sys.exit(0)
    elif cmd == 'id':
        print(driver.tega_id)
    elif cmd in ('clear', 'roots', 'old',
            'sync', 'channels', 'subscribers', 'ids',
            'global', 'forwarders', 'plugins'):
        status, reason, data = getattr(driver, cmd)()
        if data:
            print(yaml.dump(data))
        else:
            print('{} {}'.format(status, reason))

    elif cmd == 'ss':
        status, reason, data = getattr(driver, cmd)()
        print('{} {}'.format(status, reason))

    elif cmd == 'begin':
        try:
            txid = getattr(driver, cmd)()
            print('txid: {} accepted'.format(txid))
        except TransactionException as e:
            print(e)

    elif cmd == 'cand':
        try:
            data = driver.cand(python_dict=True)
            print(data)
        except TransactionException as e:
            print(e)

    elif cmd == 'cancel':
        try:
            txid = getattr(driver, cmd)()
            print('txid: {} cancelled'.format(txid))
        except TransactionException as e:
            print(e)

    elif cmd == 'commit':
        try:
            txid = getattr(driver, cmd)()
            print('txid: {} commited'.format(txid))
        except TransactionException as e:
            print(e)
    elif rpc_pattern.match(cmd):
        func_path, args, kwargs = func_args_kwargs(cmd)
        if args and kwargs:
            status, reason, data = driver.rpc(func_path, *args, **kwargs)
        elif args:
            status, reason, data = driver.rpc(func_path, *args)
        elif kwargs:
            status, reason, data = driver.rpc(func_path, **kwargs)
        else:
            status, reason, data = driver.rpc(func_path)
        if data:
            if 'result' in data:
                print(data['result'])
            else:
                print(data)
        else:
            print('{} {}'.format(status, reason))
    else:
        g = cmd_pattern.match(cmd)
        if not g:
            print('No such command "{}"'.format(cmd))
        else:
            ope = g.group(1)
            path = g.group(2)
            version = g.group(3)
            rollback = g.group(4)
            root_oid = g.group(5)
            backto = g.group(6)
            if ope == 'sub':
                driver.subscribe(path, SCOPE.GLOBAL)
            elif ope == 'subr':
                driver.subscribe(path, SCOPE.GLOBAL, regex_flag=True)
            elif ope == 'unsub':
                if path == '*':
                    driver.unsubscribe_all()
                else:
                    driver.unsubscribe(path)
            elif ope == 'unsubr':
                driver.unsubscribe(path, regex_flag=True)
            else:
                if rollback:
                    status, reason, data = getattr(driver, 'rollback')(root_oid, backto) 
                    print('{} {}'.format(status, reason))
                else:
                    body = None
                    if ope in ('put', 'pute', 'pub'):
                        buf = io.StringIO()
                        while True:
                            cmd = input()
                            if cmd == '':
                                break
                            buf.write(cmd + '\n')
                        buf.seek(0)
                        body = yaml.load(buf.read())
                        buf.close()
                    params = []
                    url_params = '' 
                    kwargs = {}
                    if ope in ('put', 'pute'):
                        instance = subtree(path, body)
                        kwargs['instance'] = instance 
                    elif ope == 'publish':
                        kwargs['channel'] = path 
                        kwargs['message'] = body 
                    elif ope == 'get' or ope == 'geta':
                        kwargs['python_dict'] = True
                        kwargs['path'] = path
                    elif ope == 'del':
                        ope = 'delete'
                        kwargs['path'] = path
                    else:
                        kwargs['path'] = path
                    if ope == 'geta':
                        ope = 'get'
                        kwargs['internal'] = True 
                    if ope == 'pute':
                        ope = 'put'
                        kwargs['ephemeral'] = True
                    if version != '':
                        kwargs['version'] = version
                    try:
                        _data = getattr(driver, ope)(**kwargs)
                        if _data:
                            print(yaml.dump(_data))
                    except CRUDException as e:
                        print(e)

def process_input(fd, events):
    '''
    Processes input.
    '''
    process_cmd(tornado_loop=True)
    prompt()

class CLISubscriber(Subscriber):

    def __init__(self, tega_id):
        super().__init__(tega_id)

    def on_init(self):
        print('--- session ready ---')
        prompt()

    def on_notify(self, notifications):
        print('')
        print('<NOTIFY>')
        print(notifications)
        prompt()

    def on_message(self, channel, tega_id, message):
        print('')
        print('<MESSAGE>')
        print('channel: {}'.format(channel))
        print('tega_id: {}'.format(tega_id))
        print('')
        print(message)
        prompt()
    
def main():
    global driver
    usage = 'usage: %prog [options] file'
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--address",
            help="REST API server host name or IP address",
            type=str, default=HOST)
    parser.add_argument("-p", "--port", help="REST API server port number",
            type=int, default=PORT)
    parser.add_argument("-t", "--tegaid", help="tega ID", type=str,
            default=str(uuid.uuid4()))
    parser.add_argument('-s', '--subscriber', help='run CLI as a subscriber',
            action='store_true', default=False)
    args = parser.parse_args()

    print('tega CLI (q: quit, h:help)')
    if args.subscriber:
        driver = Driver(args.address, args.port,
                subscriber=CLISubscriber(args.tegaid))
        ioloop = tornado.ioloop.IOLoop.current()
        ioloop.add_handler(sys.stdin, process_input, tornado.ioloop.IOLoop.READ)
        prompt()
        ioloop.run_sync(driver.subscriber_client)
    else:
        if os.path.isfile(HISTORY_FILE):
            readline.read_history_file(HISTORY_FILE)
        else:
            open(HISTORY_FILE, 'a').close()
        driver = Driver(args.address, args.port, subscriber=None)
        while True:
            try:
                process_cmd()
            except ValueError as e:
                print(e)
