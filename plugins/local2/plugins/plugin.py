import tega.idb
import tega.server
import tega.subscriber
from tega.subscriber import SCOPE

from tornado import gen
import subprocess

class Subscriber3(tega.subscriber.PlugIn):

    def __init__(self):
        super().__init__()

    def initialize(self):
        self.subscribe('call', SCOPE.GLOBAL)

    @gen.coroutine
    def on_message(self, channel, tega_id, message):
        print('*** {} on_message ***'.format(self.tega_id))
        print(channel, tega_id, message)
        print('--- rpc ---')
        result = yield self.rpc('inventory.ne1.f1', 1, 2)
        print(result)
        print('*******************************')

class Subscriber4(tega.subscriber.Subscriber):

    def initialize(self):
        self.subscribe('call', SCOPE.GLOBAL)

    @gen.coroutine
    def on_message(self, channel, tega_id, message):
        print('*** {} on_message ***'.format(self.tega_id))
        print(channel, tega_id, message)
        print('--- rpc ---')
        result = yield self.rpc('inventory.ne1.f2')
        print(result)
        print('*******************************')
