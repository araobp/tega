import unittest

import tega.tree

class TestSequence(unittest.TestCase):

    def setUp(self):

        pass

    def tearDown(self):

        pass

    def test_iter(self):
        r = tega.tree.Cont('r')
        r.a = 1
        r.b = 2
        r.c = 3
        attr_set = set([oid for oid in r])
        self.assertEqual(set(['a', 'b', 'c']), attr_set)

    def test_contains(self):
        r = tega.tree.Cont('r')
        r.a = 1
        self.assertTrue('a' in r)
        self.assertFalse('b' in r)

    def test_call(self):
        r = tega.tree.Cont('r')
        r.a = 1
        func = tega.tree.Func('id1', dict)
        r.b = func

        self.assertEqual(dict(x=1), r.b(x=1))
        with self.assertRaises(TypeError):
            r.a()

    def test_items(self):
        r = tega.tree.Cont('r')
        r.a = 1
        r.b = 2
        d0 = dict(a=1, b=2)
        d1 = {k: v for k, v in r.items()}
        self.assertEqual(d0, d1)

    def test_change(self):
        r1 = tega.tree.Cont('r1')
        r2 = tega.tree.Cont('r2')
        r1.a = 1
        r2.b = 2
        r1.a.change_(r2)
        self.assertEqual(['r2', 'a'], r1.a.qname_())
        self.assertEqual(['r2', 'a'], r2.a.qname_())

    def test_is_empty_(self):
        r = tega.tree.Cont('r')

        r.a.b
        self.assertTrue(r.a.b.is_empty_())

    def test_delete_(self):
        r = tega.tree.Cont('r')
        r.a.b = 1
        r.a.b.delete_()  # r has no subtrees. 
        self.assertTrue(r.is_empty_())

    def test__setattr__(self):
        r = tega.tree.Cont('r')

        r.a = 1
        self.assertEqual(1, r.a)

        r.a = '1'
        self.assertEqual('1', r.a)

        r.a = [1, 2]
        self.assertEqual((1, 2), r.a)

        r.a = (1, 2)
        self.assertEqual((1, 2), r.a)

        r.a = {'x': 3}
        self.assertEqual(tega.tree.Cont, type(r.a))
        self.assertEqual({'x':3}, r.a)
        self.assertEqual(3, r.a.x)

        r.a = True
        self.assertEqual(tega.tree.Bool, type(r.a))
        self.assertEqual(True, r.a)
        self.assertEqual(['r', 'a'], r.a.qname_())
        r.a = False
        self.assertEqual(False, r.a)

        r.a = tega.tree.Func('id1', max) 
        self.assertEqual(tega.tree.RPC, type(r.a))
        self.assertEqual(2, r.a(1,2))
        self.assertEqual(['r', 'a'], r.a.qname_())

        r.a = tega.tree.Func('id1', dict) 
        self.assertEqual(tega.tree.RPC, type(r.a))
        self.assertEqual(['r', 'a'], r.a.qname_())

        del r.a
        r.a[0] = 0
        r.a[1] = 1
        self.assertEqual(0, r.a[0])
        self.assertEqual(1, r.a[1])
        r.a[2].b = 'Alice'
        self.assertEqual('Alice', r.a[2].b)

    def test__getattr__(self):
        r = tega.tree.Cont('r')
        r.a
        self.assertEqual(['r', 'a'], r.a.qname_())

    def test__delattr__(self):
        r = tega.tree.Cont('r')
        r.a
        self.assertEqual(['r', 'a'], r.a.qname_())
        del r.a
        self.assertEqual(['r'], r.qname_())

    def test__getitem__(self):
        r = tega.tree.Cont('r')
        r.a = 1
        self.assertEqual(1, r.a)

    def test_extend(self):
        r = tega.tree.Cont('r')
        r.a._extend('b')
        self.assertEqual(['r', 'a', 'b'], r.a.b.qname_())
        r.a.b = 1
        r.a._extend('b')
        self.assertEqual(['r', 'a', 'b'], r.a.b.qname_())
        self.assertEqual(1, r.a.b)

    def test__call__(self):
        r = tega.tree.Cont('r')
        self.assertFalse(r.a.is_ephemeral_())

    def test_freeze_(self):
        r = tega.tree.Cont('r')
        r.a = 1
        r.b = True
        r.c = tega.tree.Func('owner_1', dict)
        r.freeze_()
        with self.assertRaises(AttributeError):
            r.a = 2
        with self.assertRaises(AttributeError):
            r.b = False
        with self.assertRaises(AttributeError):
            r.c = tega.tree.Func('owner_1', max)

    def test_immutability_check(self):
        r = tega.tree.Cont('r')
        r.a = 1
        r.b = True
        r.c = tega.tree.Func('owner_1', dict)
        r.freeze_()
        with self.assertRaises(AttributeError):
            r.a._immutability_check()
        with self.assertRaises(AttributeError):
            r.b._immutability_check()
        with self.assertRaises(AttributeError):
            r.c._immutability_check()
        with self.assertRaises(AttributeError):
            r._immutability_check()

    def test_root(self):
        r = tega.tree.Cont('r')
        r.a.b = 1
        self.assertEqual(r, r.a.b.root_())
        self.assertEqual(r, r.b.root_())
        self.assertEqual(r, r.root_())

    def test_ephemeral(self):

        r = tega.tree.Cont('r')
        r.a.b = 1
        r.a.b.ephemeral_()
        d = {'_parent': 'a', '_oid': 'b', '_version': 0, '_value': 1,
                '_ephemeral': True} 
        self.assertEqual(d, r.a.b.serialize_(internal=True))
        self.assertEqual(1, r.a.b.serialize_())
        self.assertEqual(None, r.a.b.serialize_(internal=True, serialize_ephemeral=False))

        r = tega.tree.Cont('r')
        r.a.b = 1
        r.x.y = 2
        r.o.p = 3
        r.a.ephemeral_()
        r.o.p.ephemeral_()
        self.assertEqual(dict(x=dict(y=2)), r.serialize_(serialize_ephemeral=False))

        r = tega.tree.Cont('r')
        r.a.x = 1
        r.a.y = 2
        r.b.x = 3
        r.b.y = 4
        r.a.ephemeral_()
        self.assertTrue(r.a.is_ephemeral_())
        self.assertFalse(r.b.is_ephemeral_())
        d = r.serialize_()
        self.assertTrue('a' in d)
        self.assertTrue('b' in d)
        self.assertFalse(r.a.x.is_ephemeral_())
        r.a.x.ephemeral_()
        self.assertTrue(r.a.x.is_ephemeral_())

    def test_qname(self):
        r = tega.tree.Cont('r')
        r.a.b = 1
        self.assertEqual(['r', 'a', 'b'], r.a.b.qname_())

    def test_subtree_(self):
        r = tega.tree.Cont('r')
        r.a.b = 1
        sub = r.subtree_('r.a')
        self.assertEqual(1, sub.b)

    def test_RPC(self):
        r = tega.tree.Cont('r')
        func = tega.tree.Func('id1', dict)
        r.a.b = func
        self.assertEqual('id1', r.a.b.owner_id)
        self.assertEqual(func, r.a.b)

    def test_Func(self):
        func = tega.tree.Func('id1', dict, 1, 'test', a=2, b='3')
        self.assertEqual('id1', func.owner_id)
        self.assertTrue('%id1.dict(1,"test",a=2,b="3")'==str(func) or
                        '%id1.dict(1,"test",b="3",a=2)'==str(func))
        func = tega.tree.Func('id1', dict)
        self.assertEqual(dict(a=2,b='3'), func(a=2,b='3'))
        func = tega.tree.Func('id1', dict, a=2, b='3')
        self.assertEqual(dict(a=2,b='3'), func())
        func = tega.tree.Func('id1', max)
        self.assertEqual(max(5,6), func(5,6))
        func = tega.tree.Func('id1', max, 7, 8)
        self.assertEqual(max(7,8), func())
        self.assertEqual(max, func)

    def test_Bool(self):
        r = tega.tree.Cont('r')
        r.a = True
        r.b = False
        self.assertTrue(isinstance(r.a, tega.tree.Bool))
        self.assertTrue(isinstance(r.b, tega.tree.Bool))
        self.assertTrue(r.a)
        self.assertFalse(r.b)

    def test_serialize_(self):
        r = tega.tree.Cont('r')
        r.a.b = 1
        d = {'_version': 0, '_value': 1, '_parent': 'a', '_oid': 'b',
                '_ephemeral': False}
        self.assertEqual(d, r.a.b.serialize_(internal=True))

        r.a.b = '1'
        d = {'_version': 0, '_value': '1', '_parent': 'a', '_oid': 'b',
                '_ephemeral': False}
        self.assertEqual(d, r.a.b.serialize_(internal=True))

        r.a.b = True
        d = {'_parent': 'a', '_oid': 'b', '_version': 0, '_value': True,
                '_ephemeral': False}
        self.assertEqual(d, r.a.b.serialize_(internal=True))
        self.assertEqual(True, r.a.b.serialize_())

        r.a.b = False 
        d = {'_parent': 'a', '_oid': 'b', '_version': 0, '_value': False,
                '_ephemeral': False} 
        self.assertEqual(d, r.a.b.serialize_(internal=True))
        self.assertEqual(False, r.a.b.serialize_())

        func = tega.tree.Func('id1', dict)
        r.a.b = func
        d = {'a': {'_oid': 'a', '_parent': 'r', '_version': 0, '_ephemeral':
            False, 'b': {'_oid':
            'b', '_value': '%id1.dict', '_parent': 'a', '_version':
            0, '_ephemeral': False}}, '_oid':
            'r', '_parent': None, '_version': 0, '_ephemeral': False}
        self.assertEqual(d, r.serialize_(internal=True))
        d = {'b': {'_parent': 'a', '_oid': 'b', '_version': 0, '_value':
            '%id1.dict', '_ephemeral': False}, '_oid': 'a', '_version': 0, '_parent': 'r',
            '_ephemeral': False}
        self.assertEqual(d, r.a.serialize_(internal=True))
        self.assertEqual('%id1.dict', r.a.b.serialize_())
        d = {'_version': 0, '_oid': 'b', '_value': '%id1.dict', '_parent':
                'a', '_ephemeral': False}
        self.assertEqual(d, r.a.b.serialize_(internal=True))

    def test_dumps_(self):
        r = tega.tree.Cont('r')
        r.a.b = 1
        self.assertEqual('1', r.a.b.dumps_())
        r.a.b = {'x': 1}
        self.assertEqual('{"x": 1}', r.a.b.dumps_())
        func = tega.tree.Func('id1', dict)
        r.a.b = func
        self.assertEqual('"%id1.dict"', r.a.b.dumps_())
        func = tega.tree.Func('id1', dict, a=2)
        r.a.b = func
        self.assertEqual('"%id1.dict(a=2)"', r.a.b.dumps_())

    def test_deepcopy_(self):
        r = tega.tree.Cont('r')
        r.a = dict(x=1, y=2)
        r.b = [1, 2]
        r.c = dict(x=[3, 4])
        r.d = 1
        r.e = '1'
        r.f = True
        r.g = tega.tree.Func('owner1', max)
        self.assertEqual(r.serialize_(internal=True), r.deepcopy_().serialize_(internal=True))

    def test_copy(self):
        r1 = tega.tree.Cont('r1')
        r2 = tega.tree.Cont('r2')
        r1.a = 1
        r2.a = r1.a.copy_()
        self.assertEqual(1, r2.a)
        r2.a = 2
        self.assertEqual(2, r2.a)
        r2 = r1.copy_(freeze=True)
        with self.assertRaises(AttributeError):
            r2.a = 3

    def test_merge(self):
        r1 = tega.tree.Cont('r1')
        r2 = tega.tree.Cont('r2')
        r1.a.x = 1
        r1.a.y = 2
        r1.a.z = 3
        r1.b.x = 4
        r1.b.y = 5
        r1.b.z = 6
        r2.b.x = 7
        r2.b.y = 8
        r2.b.z = 9
        r1.merge_(r2)
        data = {'b': {'z': 9, 'y': 8, 'x': 7}, 'a': {'z': 3, 'y': 2, 'x': 1}}
        self.assertEqual(data, r1.serialize_())

if __name__ == '__main__':
    unittest.main(verbosity=2)
