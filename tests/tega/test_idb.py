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
        
        # SYNC_CONFIRMED_MARKER
        tega.idb.sync_confirmed('http://localhost:8888', self.sync_path, 0, 0)

        # ver 1
        with tega.idb.tx(subscriber=self.subscriber) as t:
            inventory.ne1.location = 'Berlin'
            t.put(inventory.ne1.location)

        # ver 2
        with tega.idb.tx(subscriber=self.subscriber, policy=tega.idb.POLICY.WIN) as t:
            t.delete('inventory.ne1.location')

        # ver 3
        with tega.idb.tx(subscriber=self.subscriber, policy=tega.idb.POLICY.LOOSE) as t:
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

    def test_sync_confirmed(self):
        tega.idb.sync_confirmed('http://localhost:8888', self.sync_path, 0, 0)
        marker_confirmed = tega.idb.get_log_cache()[-1]
        confirmed = eval(marker_confirmed.lstrip('*'))
        self.assertEqual(confirmed['url'], 'http://localhost:8888')
        self.assertEqual(confirmed['sync_path'], 'inventory.ne1')
        self.assertEqual(confirmed['version'] ,0)
        self.assertEqual(confirmed['sync_ver'] ,0)

    def test_sync_confirmed_server(self):
        tega.idb.sync_confirmed_server('bahnhof_alexanderplatz', self.sync_path, 0, 0)
        marker_confirmed = tega.idb.get_log_cache()[-1]
        confirmed = eval(marker_confirmed.lstrip('*'))
        self.assertEqual(confirmed['tega_id'], 'bahnhof_alexanderplatz')
        self.assertEqual(confirmed['sync_path'], 'inventory.ne1')
        self.assertEqual(confirmed['version'] ,0)
        self.assertEqual(confirmed['sync_ver'] ,0)

    def test_build_scope_matcher(self):
        matcher = tega.idb._build_scope_matcher('a.b.c')
        self.assertTrue(matcher('a'))
        self.assertTrue(matcher('a.b'))
        self.assertTrue(matcher('a.b.c'))
        self.assertTrue(matcher('a.b.c.d'))
        self.assertFalse(matcher('a.x'))
        self.assertFalse(matcher('a.b.x'))

    def test_index_last_sync(self):
        self.set_up_idb()
        confirmed, index = tega.idb._index_last_sync()
        self.assertEqual(3, index)
        confirmed, index = tega.idb._index_last_sync(sync_path=None)
        self.assertEqual(3, index)
        confirmed, index = tega.idb._index_last_sync('inventory.ne1')
        self.assertEqual(3, index)

    def test_index_last_sync_no_sync_confirmed_marker(self):
        self.set_up_idb2()
        confirmed, index = tega.idb._index_last_sync()
        self.assertEqual(0, index)

    def test_get_last_sync_marker(self):
        self.set_up_idb()
        marker = tega.idb._get_last_sync_marker()
        self.assertEqual(marker['url'], 'http://localhost:8888')
        self.assertEqual(marker['sync_path'], 'inventory.ne1')
        self.assertEqual(marker['version'], 0)

    def test_transactions_within_scope(self):
        self.set_up_idb()
        self.set_up_idb2()
        confirmed, transactions = tega.idb.transactions_since_last_sync()
        _transactions = tega.idb._transactions_within_scope(self.sync_path, transactions)
        parent_path = '.'.join(self.sync_path.split('.')[:-1])
        notifications = tega.idb._transactions2notifications(_transactions)
        for notification in notifications:
            path = notification['path']
            self.assertTrue(path.startswith(self.sync_path) or path == parent_path)

    def test_transactions_since_last_sync(self):
        self.set_up_idb()
        confirmed, transactions = tega.idb.transactions_since_last_sync()
        self.assertEqual('!', transactions[0][0])
        self.assertEqual('Berlin', transactions[0][1][0]['instance'])
        self.assertEqual('+', transactions[1][0])
        self.assertEqual('Berlin', transactions[1][1][0]['instance'])

    def test_gen_log_cache_since_last_sync(self):
        self.set_up_idb()
        confirmed, index = tega.idb._index_last_sync()
        gen = tega.idb._gen_log_cache_since_last_sync(index)
        log = next(gen)
        instance = log['instance']
        self.assertEqual(instance, 'Berlin')

    def test_commiters(self):
        self.set_up_idb()
        commiters_list = lambda start, end: [
                self.tega_id for version in range(start,end)
                ] 
        list_a = tega.idb.commiters(self.sync_path)
        list_b = commiters_list(1, 3)  # ver 1 - ver 2

        self.assertEqual(list_a, list_b)

    def test_commiters_no_sync_confirmed_marker(self):
        self.set_up_idb2()
        commiters_list = lambda start, end: [
                self.tega_id for version in range(start,end)
                ] 
        list_a = tega.idb.commiters(self.sync_path)
        list_b = [self.tega_id, self.tega_id, self.tega_id] 

        self.assertEqual(list_a, list_b)

    def test_commiters_hash(self):
        import hashlib
        _commiters = ['id1', 'id2']
        _digest0 = hashlib.sha256('id1'.encode('utf-8')).hexdigest()
        _digest1 = hashlib.sha256('id2'.encode('utf-8')).hexdigest()
        _digest = hashlib.sha256((_digest0+_digest1).encode('utf-8')).hexdigest()

        digest = tega.idb.commiters_hash(_commiters)
        self.assertEqual(digest, _digest)

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

if __name__ == '__main__':
    unittest.main(verbosity=2)
