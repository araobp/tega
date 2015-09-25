#!/usr/bin/env python3.4

import tega.idb
import tega.server
import tega.subscriber

class Subscriber1(tega.subscriber.Subscriber):

    def __init__(self):
        super().__init__('Subscriber_1')
        tega.idb.subscribe(self, 'a.b.c')
        tega.idb.subscribe(self, 'u.v.w')
        with tega.idb.tx(subscriber=self) as t:
            a = tega.tree.Cont('a')
            a.x.f1 = tega.tree.Func('Subscriber_1', max) 
            a.x.f2 = tega.tree.Func('Subscriber_1', dict, a=1, b='2')
            a.b.c = 'FUNC_TEST' 
            t.put(a.x.f1)
            t.put(a.x.f2)
            t.put(a.b.c)

    def on_notify(self, notifications):
        print('*** subscriber 1 on_notify ****')
        print(notifications)
        print('*******************************')

    def on_message(self, message):
        print('*** subscriber 1 on_message ***')
        print(message)
        print('*******************************')

class Subscriber2(tega.subscriber.Subscriber):

    def __init__(self):
        super().__init__('Subscriber_2')
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

if __name__ == '__main__':
    Subscriber1()
    Subscriber2()
    tega.server.main()
