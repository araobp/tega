import unittest

import tega.frozendict

class TestSequence(unittest.TestCase):

    def setUp(self):

        pass

    def tearDown(self):

        pass

    def test_path2qname(self):
        dict_ = tega.frozendict.frozendict(a=1, b='berlin')
        self.assertTrue('(a=1,b=berlin)' == repr(dict_) or
                '(b=berlin,a=1)' == repr(dict_))

if __name__ == '__main__':
    unittest.main(verbosity=2)

