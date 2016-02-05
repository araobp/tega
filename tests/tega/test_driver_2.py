import tega.tree
import tega.driver

import signal
import unittest
import os
import subprocess
import time

script_dir = os.getcwd() + '/servers'
#print('script dir: ' + script_dir)

class TestSequence(unittest.TestCase):
    '''
           [global]
            /   \     
          /       \
        /           \
    [local1]     [local2]
    '''
    process_g = None
    process_l1 = None
    process_l2 = None
    driver_g = None
    driver_l1 = None
    driver_l2 = None

    @classmethod
    def setUpClass(cls):

        TestSequence.process_g = subprocess.Popen(
                ['{}/global'.format(script_dir), script_dir],
                preexec_fn=os.setsid)

        time.sleep(2)

        TestSequence.process_l1 = subprocess.Popen(
                ['{}/local1_plugin'.format(script_dir), script_dir],
                preexec_fn=os.setsid)

        time.sleep(2)

        TestSequence.process_l2 = subprocess.Popen(
                ['{}/local2'.format(script_dir), script_dir],
                preexec_fn=os.setsid)

        time.sleep(2)

        TestSequence.driver_g = tega.driver.Driver('localhost', 8888, 'driver_g')
        TestSequence.driver_l1 = tega.driver.Driver('localhost', 8889, 'driver_l1')
        TestSequence.driver_l2 = tega.driver.Driver('localhost', 8890, 'driver_l2')

        time.sleep(2)

    def setUp(self):

        pass

    def tearDown(self):

        TestSequence.driver_g.clear()
        TestSequence.driver_l1.clear()
        TestSequence.driver_l2.clear()
        time.sleep(2)

    @classmethod
    def tearDownClass(cls):

        os.killpg(TestSequence.process_g.pid, signal.SIGTERM)
        os.killpg(TestSequence.process_l1.pid, signal.SIGTERM)
        os.killpg(TestSequence.process_l2.pid, signal.SIGTERM)

    #def test_(self):
    #    time.sleep(1000)

    def test_rpc(self):
        F1 = 'inventory.ne1.f1'
        F2 = 'inventory.ne1.f2'

        # rpc from "global" to "local1"
        status, reason, result = TestSequence.driver_g.rpc(F1, 1, 2)
        self.assertEqual(200, status)
        self.assertEqual(2, result)
        status, reason, result = TestSequence.driver_g.rpc(F2)
        self.assertEqual(200, status)
        self.assertEqual(6, len(result.split()))  # Tue Jul 14 22:32:37 JST 2015

        # rpc from "local2" to "local1" via "global"
        status, reason, result = TestSequence.driver_l2.rpc(F1, 1, 2)
        self.assertEqual(200, status)
        self.assertEqual(2, result)
        status, reason, result = TestSequence.driver_l2.rpc(F2)
        self.assertEqual(200, status)
        self.assertEqual(6, len(result.split()))  # Tue Jul 14 22:32:37 JST 2015

    '''
    2016/2/5

    tega's collision detection and sync mechanism will be changed.


    def test_sync(self):
        inv = tega.tree.Cont('inventory')
        inv.ne1.b = 1
        TestSequence.driver_l1.put(inv)
        inv.ne1.c = 2
        TestSequence.driver_l1.put(inv.ne1.c)
        time.sleep(1)
        self.assertEqual({'ne1': {'b': 1, 'c': 2}}, TestSequence.driver_g.get('inventory').serialize_())

    def test_sync_after_clear(self):
        inv = tega.tree.Cont('inventory')
        inv.ne1.b = 1
        TestSequence.driver_l1.put(inv)
        inv.ne1.c = 2
        TestSequence.driver_l1.put(inv.ne1.c)
        time.sleep(1)
        self.assertEqual({'ne1': {'b': 1, 'c': 2}}, TestSequence.driver_g.get('inventory').serialize_())
        TestSequence.driver_g.clear()
        TestSequence.driver_l1.sync()
        self.assertEqual({'ne1': {'b': 1, 'c': 2}}, TestSequence.driver_g.get('inventory').serialize_())

        print("===== driver_g.log =====")
        print(TestSequence.driver_g.log()[2])
        print("===== driver_l1.log ====")
        print(TestSequence.driver_l1.log()[2])
        '''

if __name__ == '__main__':
    unittest.main(verbosity=2)


