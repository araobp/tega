import tega.idb
import tega.server
import tega.subscriber
from tega.subscriber import SCOPE

from tornado import gen
import subprocess

class Subscriber1(tega.subscriber.PlugIn):

    def __init__(self):
        super().__init__()

    def initialize(self):
        self.subscribe('call', SCOPE.GLOBAL)
        with self.tx() as t:
            a = tega.tree.Cont('a')
            inventory = tega.tree.Cont('inventory')
            a.x.f1 = self.func(max, 1, 2) 
            a.x.f2 = self.func(dict, a=1, b='2') 
            a.x.f3 = self.func(max) 
            a.x.f4 = self.func(dict) 
            a.b.c = 'FUNC_TEST' 
            t.put(a.x)
            t.put(a.b.c)
            inventory.ne1.f1 = self.func(max)
            t.put(inventory.ne1.f1)
            inventory.ne1.f2 = self.func(self.date)
            t.put(inventory.ne1.f2)

    def on_notify(self, notifications):
        print('*** subscriber 1 on_notify ****')
        print(notifications)
        print('*******************************')

    @gen.coroutine
    def on_message(self, channel, tega_id, message):
        print('*** subscriber 1 on_message ***')
        print(channel, tega_id, message)
        result = yield self.rpc('inventory.ne1.f2')
        print(result)
        print('*******************************')

    def date(self):
        result = subprocess.check_output(['date'])
        return str(result, encoding='utf-8')

class Subscriber2(tega.subscriber.Subscriber):

    def initialize(self):
        tega.idb.subscribe(self, 'd.e.f')
        tega.idb.subscribe(self, 'x.y.z')

    def on_notify(self, notifications):
        print('*** subscriber 2 on_notify ****')
        print(notifications)
        print('*******************************')

    def on_message(self, message):
        print('*** subscriber 2 on_message ***')
        print(message)
        print('*******************************')
