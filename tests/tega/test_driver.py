import tega.tree
import tega.driver

import signal
import unittest
import os
import subprocess
import time

script_dir = os.getcwd() + '/servers'
print('script dir: ' + script_dir)

class TestSequence(unittest.TestCase):

    process_g = None
    process_l1 = None
    driver_g = None
    driver_l1 = None

    @classmethod
    def setUpClass(cls):

        TestSequence.process_g = subprocess.Popen(
                ['{}/global'.format(script_dir), script_dir],
                preexec_fn=os.setsid)

        TestSequence.process_l1 = subprocess.Popen(
                ['{}/local1'.format(script_dir), script_dir],
                preexec_fn=os.setsid)

        time.sleep(3)

        TestSequence.driver_g = tega.driver.Driver('localhost', 8888, 'driver_g')
        TestSequence.driver_l1 = tega.driver.Driver('localhost', 8889, 'driver_l1')

    def setUp(self):

        pass

    def tearDown(self):

        TestSequence.driver_g.clear()
        TestSequence.driver_l1.clear()

    @classmethod
    def tearDownClass(cls):

        os.killpg(TestSequence.process_g.pid, signal.SIGTERM)
        os.killpg(TestSequence.process_l1.pid, signal.SIGTERM)

    def test_clear(self):

        a = tega.tree.Cont('a')
        a.b.c = 1
        TestSequence.driver_g.put(a.b.c)
        TestSequence.driver_g.clear()
        status, reason, body = TestSequence.driver_g.roots()
        self.assertFalse(body)

    def test_log(self):

        '''
        TODO: impl.
        '''

    def test_roots(self):

        a = tega.tree.Cont('a')
        a.b.c = 1
        x = tega.tree.Cont('x')
        x.y.z = 2
        TestSequence.driver_g.put(a.b.c)
        TestSequence.driver_g.put(x)
        status, reason, body = TestSequence.driver_g.roots()
        self.assertEqual('OK', reason)
        self.assertEqual(0, body['a'])
        self.assertEqual(0, body['x'])
        self.assertEqual(2, len(body))

    def test_old(self):

        a = tega.tree.Cont('a')
        x = tega.tree.Cont('x')

        a.b.c = 1
        x.y.z = 2
        TestSequence.driver_g.put(a.b.c)
        TestSequence.driver_g.put(x.y.z)

        a.b.C = 3
        x.y.Z = 4
        TestSequence.driver_g.put(a.b.C)
        TestSequence.driver_g.put(x.y.Z)

        a.B.C = 5
        TestSequence.driver_g.put(a.B.C)

        status, reason, body = TestSequence.driver_g.old()
        for old_ in body:
            if 'a' in old_:
                self.assertEqual([0, 1], old_['a'])
            elif 'x' in old_:
                self.assertEqual([0], old_['x'])
            else:
                raise Exception('old')

    def test_rollback(self):

        import tega.tree
        a = tega.tree.Cont('a')

        a.b.c = 0
        TestSequence.driver_g.put(a.b.c)
        a.b.c = 1
        TestSequence.driver_g.put(a.b.c)

        data = TestSequence.driver_g.get('a.b.c')
        self.assertEqual(1, data)

        TestSequence.driver_g.rollback('a', -1)
        data = TestSequence.driver_g.get('a.b.c')
        self.assertEqual(0, data)

    def test_put(self):

        import tega.tree
        a = tega.tree.Cont('a')

        a.b.c = 0
        TestSequence.driver_g.put(a.b.c)
        data = TestSequence.driver_g.get('a.b.c')
        self.assertEqual(0, data)

        a.b.c = '0'
        TestSequence.driver_g.put(a)
        data = TestSequence.driver_g.get('a.b.c')
        self.assertEqual('0', data)

        a.b.c = '0'
        TestSequence.driver_g.put(a.b)
        data = TestSequence.driver_g.get('a.b.c')
        self.assertEqual('0', data)

        a.b.c = '0'
        TestSequence.driver_g.put(a.b.c)
        data = TestSequence.driver_g.get('a.b.c')
        self.assertEqual('0', data)

        a.b.c = [1, 2, 3] 
        TestSequence.driver_g.put(a.b.c)
        data = TestSequence.driver_g.get('a.b.c')
        self.assertEqual((1, 2, 3), data)

        a.b.c = dict(x=1, y=dict(z='2')) 
        TestSequence.driver_g.put(a.b.c)
        data = TestSequence.driver_g.get('a.b.c').serialize_()
        self.assertEqual(dict(x=1, y=dict(z='2')), data)

    def test_delete(self):

        import tega.tree
        import tega.driver.driver
        a = tega.tree.Cont('a')

        a.b.c = 0
        TestSequence.driver_g.put(a.b.c)
        data = TestSequence.driver_g.get('a.b.c')
        self.assertEqual(0, data)

        TestSequence.driver_g.delete('a.b.c')
        self.assertRaises(tega.driver.driver.CRUDException,
                TestSequence.driver_g.get, 'a.b.c')

    def test_get(self):

        import tega.tree
        import tega.driver.driver
        a = tega.tree.Cont('a')

        a.b.c = 0
        TestSequence.driver_g.put(a.b.c)
        data = TestSequence.driver_g.get('a.b.c')
        self.assertEqual(0, data)

        a.b.c = 1
        TestSequence.driver_g.put(a.b.c)
        data = TestSequence.driver_g.get('a.b.c', version=0)
        self.assertEqual(0, data)
        data = TestSequence.driver_g.get('a.b.c', version=1)
        self.assertEqual(1, data)

    def test_put_version(self):

        import tega.tree
        import tega.driver.driver
        a = tega.tree.Cont('a')

        a.b.c = 0
        TestSequence.driver_g.put(a.b.c)
        a.b.c = 1
        self.assertRaises(tega.driver.driver.CRUDException,
                TestSequence.driver_g.put, a.b.c, version=1)

    def test_delete_version(self):

        import tega.tree
        import tega.driver.driver
        a = tega.tree.Cont('a')

        a.b.c = 0
        TestSequence.driver_g.put(a.b.c)
        a.b.c = 1
        self.assertRaises(tega.driver.driver.CRUDException,
                TestSequence.driver_g.delete, 'a.b.c', version=1)

    def test_delete_version(self):

        import tega.tree
        import tega.driver.driver
        a = tega.tree.Cont('a')

        a.b.c = 0
        TestSequence.driver_g.put(a.b.c)
        a.b.c = 1
        self.assertRaises(tega.driver.driver.CRUDException,
                TestSequence.driver_g.get, 'a.b.c', version=1)

    def test_begin(self):
        '''
        TODO: timeout case
        '''
        txid = TestSequence.driver_g.begin()
        self.assertEqual(str, type(txid))

        # Duplicated begin()
        self.assertRaises(tega.driver.driver.TransactionException,
                TestSequence.driver_g.begin)
        TestSequence.driver_g.cancel()

    def test_cancel(self):
        '''
        TODO: timeout case
        '''
        txid = TestSequence.driver_g.begin()
        self.assertEqual(str, type(txid))
        txid = TestSequence.driver_g.cancel()

        # Duplicated begin()
        self.assertRaises(tega.driver.driver.TransactionException,
                TestSequence.driver_g.cancel)

    def test_commit(self):
        '''
        TODO: timeout case
        '''
        txid = TestSequence.driver_g.begin()
        import tega.tree
        import tega.driver.driver
        a = tega.tree.Cont('a')
        a.b.c = 'Paris'
        self.assertEqual(str, type(txid))
        TestSequence.driver_g.put(a.b.c)
        self.assertRaises(tega.driver.driver.CRUDException,
                TestSequence.driver_g.get, 'a.b.c')
        TestSequence.driver_g.commit()
        self.assertEqual('Paris', TestSequence.driver_g.get('a.b.c'))

    def test_idb_edges(self):

        def _edges_set(edges):
            return ['{}-{}'.format(*edge) for edge in edges]

        r = tega.tree.Cont('r')
        r.a.x = 1
        r.a.y = 2
        r.a.z = 3
        r.b.x = 4
        r.b.y = 5
        r.b.z = 6
        txid = TestSequence.driver_g.begin()
        TestSequence.driver_g.put(r.a)
        TestSequence.driver_g.commit()
        txid = TestSequence.driver_g.begin()
        TestSequence.driver_g.put(r.b)
        TestSequence.driver_g.commit()

        data_compared = [['r(1)', 'r.b(1)'], ['r.b(1)', 'r(1)'], ['r.b(1)',
            'r.b.y(1)'], ['r.b.y(1)', 'r.b(1)'], ['r.b(1)', 'r.b.z(1)'],
            ['r.b.z(1)', 'r.b(1)'], ['r.b(1)', 'r.b.x(1)'], ['r.b.x(1)',
                'r.b(1)'], ['r(1)', 'r.a(0)'], ['r.a(0)', 'r(1)'], ['r.a(0)',
                    'r.a.y(0)'], ['r.a.y(0)', 'r.a(0)'], ['r.a(0)', 'r.a.z(0)'],
                ['r.a.z(0)', 'r.a(0)'], ['r.a(0)', 'r.a.x(0)'], ['r.a.x(0)',
                    'r.a(0)'], ['r(0)', 'r.a(0)'], ['r.a(0)', 'r(1)'],
                ['r.a(0)', 'r.a.y(0)'], ['r.a.y(0)', 'r.a(0)'], ['r.a(0)',
                    'r.a.z(0)'], ['r.a.z(0)', 'r.a(0)'], ['r.a(0)', 'r.a.x(0)'],
                ['r.a.x(0)', 'r.a(0)']]
        _, _, data = TestSequence.driver_g.edges(old_roots=True)
        data0 = _edges_set(data)
        data1 = _edges_set(data_compared)
        self.assertEqual(set(data0), set(data1))

        data_compared = [['r(1)', 'r.b(1)'], ['r.b(1)', 'r(1)'], ['r.b(1)',
            'r.b.y(1)'], ['r.b.y(1)', 'r.b(1)'], ['r.b(1)', 'r.b.z(1)'],
            ['r.b.z(1)', 'r.b(1)'], ['r.b(1)', 'r.b.x(1)'], ['r.b.x(1)',
                'r.b(1)'], ['r(1)', 'r.a(0)'], ['r.a(0)', 'r(1)'], ['r.a(0)',
                    'r.a.y(0)'], ['r.a.y(0)', 'r.a(0)'], ['r.a(0)', 'r.a.z(0)'],
                ['r.a.z(0)', 'r.a(0)'], ['r.a(0)', 'r.a.x(0)'], ['r.a.x(0)',
                    'r.a(0)']]
        _, _, data = TestSequence.driver_g.edges(old_roots=False)
        data0 = _edges_set(data)
        data1 = _edges_set(data_compared)
        self.assertEqual(set(data0), set(data1))
        _, _, data = TestSequence.driver_g.edges(root_oid='r')
        data0 = _edges_set(data)
        self.assertEqual(set(data0), set(data1))

if __name__ == '__main__':
    unittest.main(verbosity=2)


