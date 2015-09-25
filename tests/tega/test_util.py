import unittest

import tega.frozendict
import tega.util

class TestSequence(unittest.TestCase):

    def setUp(self):

        pass

    def tearDown(self):

        pass
    
    def test_path2qname(self):

        qname = tega.util.path2qname('a.b.c')
        self.assertEqual(['a', 'b', 'c'], qname)
        
        qname = tega.util.path2qname('a.b(x=1, y=Berlin).c')
        self.assertEqual(['a', 'b',
            tega.frozendict.frozendict(x=1,y='Berlin'), 'c'], qname)

    def test_qname2path(self):

        path = tega.util.qname2path(['a', 'b', 'c'])
        self.assertEqual('a.b.c', path) 

        path = tega.util.qname2path(['a', 'b',
            tega.frozendict.frozendict(x=1, y='Berlin'), 'c'])
        self.assertTrue('a.b(x=1,y=Berlin).c' == path or
                'a.b(y=Berlin,x=1).c' == path)

    def test_url2path(self):

        path = tega.util.url2path('/a/b/c/')
        self.assertEqual('a.b.c', path) 

        path = tega.util.url2path('/a/b/c')
        self.assertEqual('a.b.c', path) 

    def test_path2url(self):

        url = tega.util.path2url('a.b.c')
        self.assertEqual('/a/b/c/', url) 

    def test_instance2url(self):

        import tega.tree

        a = tega.tree.Cont('a')
        a.b.c
            
        url = tega.util.instance2url(a.b.c)
        self.assertEqual('/a/b/c/', url) 

        a = tega.tree.Cont('a')
        a.b(x=1).c

        url = tega.util.instance2url(a.b(x=1).c)
        self.assertEqual('/a/b(x=1)/c/', url)

        a = tega.tree.Cont('a')
        a.b(x=1,y='Berlin').c

        url = tega.util.instance2url(a.b(x=1,y='Berlin').c)
        self.assertTrue('/a/b(x=1,y=Berlin)/c/' == url or
                '/a/b(y=Berlin,x=1)/c/' == url)

    def test_dict2cont(self):

        dict_ = dict(a=dict(b=dict(c=1)))
        a = tega.util.dict2cont(dict_)
        self.assertEqual(1, a.b.c)
        self.assertEqual(['a', 'b', 'c'], a.b.c.qname_())
        self.assertEqual(['a', 'b'], a.b.qname_())
        self.assertEqual(['a'], a.qname_())

        dict_ = dict(a=dict(b=dict(c=[1, 2, 3])))
        a = tega.util.dict2cont(dict_)
        self.assertEqual((1, 2, 3), a.b.c)
        self.assertEqual(['a', 'b', 'c'], a.b.c.qname_())
        self.assertEqual(['a', 'b'], a.b.qname_())
        self.assertEqual(['a'], a.qname_())

    def test_subtree(self):

        dict_ = dict(b=dict(c=1))
        a = tega.util.subtree('a', dict_)
        self.assertEqual(1, a.b.c)
        self.assertEqual(['a', 'b', 'c'], a.b.c.qname_())
        self.assertEqual(['a', 'b'], a.b.qname_())
        self.assertEqual(['a'], a.qname_())

        dict_ = dict(b=dict(c=[1, 2, 3]))
        a = tega.util.subtree('a', dict_)
        self.assertEqual((1, 2, 3), a.b.c)
        self.assertEqual(['a', 'b', 'c'], a.b.c.qname_())
        self.assertEqual(['a', 'b'], a.b.qname_())
        self.assertEqual(['a'], a.qname_())

    '''
    def test_plugins(self):

        import os
        import tega.idb
        plugin_path = os.getcwd()
        classes = tega.util.plugins(plugin_path)
        self.assertEqual('Subscriber1', classes[0].__name__)
        self.assertEqual('Subscriber_1', classes[0]().tega_id)
        self.assertEqual("('a', 'b'),{'c': 'd'}", classes[0]().rpc1('a', 'b', c='d'))
        self.assertEqual('Subscriber2', classes[1].__name__)
        self.assertEqual('Subscriber_2', classes[1]().tega_id)
    '''

    def test_func_args_kwargs(self):
        f = "r.a.b(1, '2', id=3, name='Alice')"
        func, args, kwargs = tega.util.func_args_kwargs(f)
        self.assertEqual('r.a.b', func)
        self.assertEqual([1, '2'], args)
        self.assertEqual(dict(id=3,name='Alice'), kwargs)
        f = "r.a.b"
        func, args, kwargs = tega.util.func_args_kwargs(f)
        self.assertEqual('r.a.b', func)
        self.assertEqual(None, args)
        self.assertEqual(None, kwargs)

if __name__ == '__main__':
    unittest.main(verbosity=2)
