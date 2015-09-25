import tega.subscriber
from tega.tree import Cont

import logging
from tornado import gen
import tornado.httpclient
from html.parser import HTMLParser

class WGU624(tega.subscriber.PlugIn):
    '''
    NETGEAR WGU624
    '''
    BASE_URL = 'http://192.168.1.1'
    INDEX = 'index.htm'
    LOG = 'log.html'
    PATH = 'inventory.homenet.wgu624'
    PATH_USERNAME = PATH + '.credential.username'
    PATH_PASSWORD = PATH + '.credential.password'

    def __init__(self):
        super().__init__()

    def initialize(self):
        tornado.httpclient.AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
        #self.conn = tornado.httpclient.AsyncHTTPClient()
        self.conn = tornado.httpclient.HTTPClient()
        inv = Cont('inventory')
        inv.homenet.wgu624.log = self.func(self.get_log)
        with self.tx() as t:
            t.put(inv.homenet.wgu624.log)

    def on_notify(self, notifications):
        pass

    def on_message(self, channel, tega_id, message):
        pass

    #@gen.coroutine
    def get_log(self):
        # TODO: this part should be in initalize()
        try:
            self.username = self.get(self.PATH_USERNAME)
            self.password = self.get(self.PATH_PASSWORD)
        except KeyError:
            self.username = None
            self.password = None
        logging.debug('username: {}, password: {}'.format(self.username,
                                                          self.password))
        url = '{}/{}'.format(self.BASE_URL, self.LOG)
        request = tornado.httpclient.HTTPRequest(url=url, method='GET',
                auth_username=self.username, auth_password=self.password,
                auth_mode='basic')
        #response = yield self.conn.fetch(request)
        #raise gen.Return(response.body.decode('shift-jis'))
        response =  self.conn.fetch(request)
        doc = response.body.decode('shift-jis')
        print(doc)
        parser = NetgearLog()
        parser.feed(doc) 
        return parser.log 

class NetgearLog(HTMLParser):
    textarea = False
    _log = None
    def handle_starttag(self, tag, attrs):
        if tag == 'textarea':
            self.textarea = True
    def handle_endtag(self, tag):
        if self.textarea:
            self.textarea = False
    def handle_data(self, data):
        if self.textarea:
            self._log = data.lstrip('\n')
    @property
    def log(self):
        return self._log
