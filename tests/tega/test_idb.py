import os
import unittest

import tega.idb
import tega.tree

tega_id = 'test_idb'
script_dir = os.getcwd() + '/servers'

class MockSubscriber(object):

    def __init__(self):
        self.tega_id = 'ne1_appl'

    def on_notify(self, notifications):
        pass

class TestSequence(unittest.TestCase):

    def setUp(self):
        tega.idb.start(script_dir, tega_id)
        self.subscriber = MockSubscriber()
        self.sync_path = 'inventory.ne1'
        self.tega_id = 'ne1_appl'
        tega.idb.subscribe(self.subscriber, self.sync_path)

    def tearDown(self):
        tega.idb.clear()
        tega.idb.stop()

    def set_up_idb(self):

        inventory = tega.tree.Cont('inventory')

        # ver 0
        with tega.idb.tx(subscriber=self.subscriber) as t:
            inventory.ne1.name = 'NE1'
            inventory.ne1.address = '10.10.10.10/24'
            t.put(inventory)
        
        # ver 1
        with tega.idb.tx(subscriber=self.subscriber) as t:
            inventory.ne1.location = 'Berlin'
            t.put(inventory.ne1.location)

        # ver 2
        with tega.idb.tx(subscriber=self.subscriber) as t:
            t.delete('inventory.ne1.location')

        # ver 3
        with tega.idb.tx(subscriber=self.subscriber) as t:
            inventory.ne2.name = 'Tokyo'
            t.put(inventory.ne2.name)

    def set_up_idb2(self):

        inventory = tega.tree.Cont('inventory')
        topology = tega.tree.Cont('topology')

        # ver 0
        with tega.idb.tx(subscriber=self.subscriber) as t:
            topology.ne1.name = 'NE1'
            t.put(topology)

        # ver 1
        with tega.idb.tx(subscriber=self.subscriber) as t:
            inventory.ne2.name = 'NE2'
            t.put(inventory)
            inventory.ne1.weather = 'fine'
            t.put(inventory)

        # ver 2
        with tega.idb.tx(subscriber=self.subscriber) as t:
            t.delete('inventory')

    def test_is_started(self):
        self.assertTrue(tega.idb.is_started())

    def test_put(self):
        with tega.idb.tx() as t:
            t.put(path='a.b', instance=dict(c=1))
        self.assertEqual(tega.idb.get(path='a'), {'b': {'c': 1}})
        self.assertEqual(tega.idb.get(path='a.b.c'), 1)

        a = tega.tree.Cont('a')
        a.b.c = 1
        with tega.idb.tx() as t:
            t.put(a.b.c)
        self.assertEqual(tega.idb.get(path='a'), {'b': {'c': 1}})
        self.assertEqual(tega.idb.get(path='a'), a)
        self.assertEqual(tega.idb.get(path='a.b.c'), 1)


    def test_transaction2notifications(self):
        transactions = [['!', [dict(a=1), dict(b=2)]], ['+', [dict(c=3)]]]
        notifications = tega.idb._transactions2notifications(transactions)
        keys = set(['a', 'b', 'c'])
        self.assertEqual(3, len(notifications))
        self.assertTrue(dict(a=1) in notifications)
        self.assertTrue(dict(b=2) in notifications)
        self.assertTrue(dict(c=3) in notifications)

    def test_build_scope_matcher(self):
        matcher = tega.idb._build_scope_matcher('a.b.c')
        self.assertTrue(matcher('a'))
        self.assertTrue(matcher('a.b'))
        self.assertTrue(matcher('a.b.c'))
        self.assertTrue(matcher('a.b.c.d'))
        self.assertFalse(matcher('a.x'))
        self.assertFalse(matcher('a.b.x'))

    def test_get_version(self):
        self.set_up_idb()
        self.assertEqual(0, tega.idb.get_version('inventory.ne1.name'))
        self.assertEqual(0, tega.idb.get_version('inventory.ne1.address'))
        self.assertEqual(2, tega.idb.get_version('inventory.ne1'))
        self.assertEqual(3, tega.idb.get_version('inventory.ne2.name'))
        self.assertEqual(3, tega.idb.get_version('inventory.ne2'))
        self.assertEqual(3, tega.idb.get_version('inventory'))

    def test_ephemeral_nodes(self):
        OWNER = 'owner1'
        r = tega.tree.Cont('r')
        tega.idb.add_tega_id(OWNER)
        with tega.idb.tx(tega_id=OWNER) as t:
            r.a.b = 1
            r.a.c = 2
            r.A.b = 3
            r.B.c = 4
            t.put(r.a.b)
            t.put(r.a.c, ephemeral=True)
            t.put(r.A)
            t.put(r.B, ephemeral=True)

        instance = tega.idb.get('r.a')
        d1a = {'b': 1}
        d1b = {'b': 1, 'c': 2}
        d2a = instance.serialize_(serialize_ephemeral=False)
        d2b = instance.serialize_()
        self.assertEqual(d1a, d2a)
        self.assertEqual(d1b, d2b)

        def _non_ephemeral_node():
            with tega.idb.tx(tega_id=OWNER) as t:
                r.a.b = 1
                t.put(r.a.b, ephemeral=True)
        self.assertRaises(Exception, _non_ephemeral_node)

        instance = tega.idb.get('r')
        d1a = {'a': {'b': 1}, 'A': {'b': 3}}
        d1b = {'a': {'b': 1, 'c': 2}, 'A': {'b': 3}, 'B': {'c': 4}}
        d2a = instance.serialize_(serialize_ephemeral=False)
        d2b = instance.serialize_()
        self.assertEqual(d1a, d2a)
        self.assertEqual(d1b, d2b)

        tega.idb.remove_tega_id(OWNER)
        instance = tega.idb.get('r.a')
        d3 = instance.serialize_()
        d1a = {'b': 1}
        self.assertEqual(d1a, d3)

    def test_loglist_for_sync(self):
        r = tega.tree.Cont('r')
        r.a.b = 1
        r.a.c = 2
        r.a.d = 3
        r.a.e = 4
        r.a.f = 5
        r.a.g = 6
        r.a.h = 7
        r.a.i = 8
        r.a.j = 9

        # ver 0
        with tega.idb.tx(subscriber = self.subscriber) as t:
            t.put(r.a.b)
            t.put(r.a.c)
        # ver 1
        with tega.idb.tx(subscriber = self.subscriber) as t:
            t.delete(path='r.a.c')
            t.put(r.a.d)
        tega.idb.save_snapshot(tega_id)

        # ver 2
        with tega.idb.tx(subscriber = self.subscriber) as t:
            t.put(r.a.e)
            t.put(r.a.f)
            t.delete(path='r.a.f')
        # ver 3
        with tega.idb.tx(subscriber = self.subscriber) as t:
            t.put(r.a.g)
        tega.idb.save_snapshot(tega_id)

        # ver 4
        with tega.idb.tx(subscriber = self.subscriber) as t:
            t.put(r.a.h)

        # ver 5
        tega.idb.rollback(tega_id=tega_id, root_oid='r', backto=-1,
                subscriber=self.subscriber)

        # ver 6
        with tega.idb.tx(subscriber = self.subscriber) as t:
            t.put(r.a.i)
            t.delete(path='r.a.i')
            t.put(r.a.j)

        '''
        print(tega.idb.loglist_for_sync('r', 0))
        print(tega.idb.loglist_for_sync('r', 3))
        print(tega.idb.loglist_for_sync('r', 5))
        print(tega.idb.loglist_for_sync('r', 6))
        '''

        data0 = [[{'instance': 2, 'tega_id': 'ne1_appl', 'path': 'r.a.c', 'ope': 'DELETE'},
                {'instance': 3, 'tega_id': 'ne1_appl', 'path': 'r.a.d', 'ope': 'PUT'}],
                [{'instance': 4, 'tega_id': 'ne1_appl', 'path': 'r.a.e', 'ope': 'PUT'},
                {'instance': 5, 'tega_id': 'ne1_appl', 'path': 'r.a.f', 'ope': 'PUT'},
                {'instance': 5, 'tega_id': 'ne1_appl', 'path': 'r.a.f', 'ope': 'DELETE'}],
                [{'instance': 6, 'tega_id': 'ne1_appl', 'path': 'r.a.g', 'ope': 'PUT'}],
                [{'instance': 7, 'tega_id': 'ne1_appl', 'path': 'r.a.h', 'ope': 'PUT'}],
                [{'instance': None, 'tega_id': 'test_idb', 'backto': -1, 'ope': 'ROLLBACK', 'path': 'r'}],
                [{'instance': 8, 'tega_id': 'ne1_appl', 'path': 'r.a.i', 'ope': 'PUT'}, {'instance': 8, 'tega_id': 'ne1_appl', 'path': 'r.a.i', 'ope': 'DELETE'}, {'instance': 9, 'tega_id': 'ne1_appl', 'path': 'r.a.j', 'ope': 'PUT'}]]

        data1 = [[{'instance': 7, 'tega_id': 'ne1_appl', 'path': 'r.a.h', 'ope': 'PUT'}],
                [{'instance': None, 'tega_id': 'test_idb', 'backto': -1, 'ope': 'ROLLBACK', 'path': 'r'}],
                [{'instance': 8, 'tega_id': 'ne1_appl', 'path': 'r.a.i', 'ope': 'PUT'},
                {'instance': 8, 'tega_id': 'ne1_appl', 'path': 'r.a.i', 'ope': 'DELETE'},
                {'instance': 9, 'tega_id': 'ne1_appl', 'path': 'r.a.j', 'ope': 'PUT'}]]

        data2 = [[{'instance': 8, 'tega_id': 'ne1_appl', 'path': 'r.a.i', 'ope': 'PUT'},
                {'instance': 8, 'tega_id': 'ne1_appl', 'path': 'r.a.i', 'ope': 'DELETE'},
                {'instance': 9, 'tega_id': 'ne1_appl', 'path': 'r.a.j', 'ope': 'PUT'}]]

        data3 = []

        self.assertEqual(data0,tega.idb.loglist_for_sync('r', 0))
        self.assertEqual(data1, tega.idb.loglist_for_sync('r', 3))
        self.assertEqual(data2, tega.idb.loglist_for_sync('r', 5))
        self.assertEqual(data3, tega.idb.loglist_for_sync('r', 6))

if __name__ == '__main__':
    unittest.main(verbosity=2)
