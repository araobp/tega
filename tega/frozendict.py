"""
Copyright (c) 2012 Santiago Lezica

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTAB

----------
(source) https://github.com/slezica/python-frozendict

"""

import collections, operator
from functools import reduce

class frozendict(collections.Mapping):

    def __init__(self, *args, **kwargs):
        self.__dict = dict(*args, **kwargs)
        self.__hash = None

    def __getitem__(self, key):
        return self.__dict[key]

    def copy(self, **add_or_replace):
        return frozendict(self, **add_or_replace)

    def __iter__(self):
        return iter(self.__dict)

    def __len__(self):
        return len(self.__dict)

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        #return '<frozendict %s>' % repr(self.__dict)
        repr_ = [] 
        for k,v in self.__dict.items():
            repr_.append('{}={}'.format(k, v))
        kvs = ','.join(repr_)
        return '({})'.format(kvs)

    def __hash__(self):
        if self.__hash is None:
            self.__hash = reduce(operator.xor, list(map(hash, iter(self.items()))), 0)

        return self.__hash

