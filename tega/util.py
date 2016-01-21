from tega.frozendict import frozendict

import copy
import os

def path2qname(path):
    '''
    path('a.b.c') to qname(['a', 'b', 'c'])
    '''
    qname = []
    for v in path.split('.'):
        if v.endswith(')'): # aaa(a=1, b=2)
            v_v = v.rstrip(')').split('(')  # ['aaa', 'a=1, b=2']
            args = v_v[1].replace(' ', '').split(',')  # ['a=1, 'b=2']
            kwargs = {}
            for arg in args:
                kv = arg.split('=')
                k_ = kv[0]
                v_ = kv[1]
                if v_.isdigit():
                    v_ = int(v_)
                kwargs[k_] = v_
            dict_ = frozendict(**kwargs)  # (a=1, b=2)
            qname.append(v_v[0])  # 'aaa'
            qname.append(dict_)  # (a=1, b=2)
        elif v.endswith(']'):
            v_v = v.rstrip(']').split('[')
            k_ = v_v[0]
            k_dim = v_v[1]
            qname.append(k_)
            qname.append(k_dim)
        else:
            qname.append(v)
    return qname

def qname2path(qname):
    '''
    qname(['a', 'b', 'c']) to path('a.b.c')
    '''
    path = ''
    for v in qname:
        if type(v) == frozendict:
            path = path + str(v)
        elif type(v) == int:
            path = path + '.' + str(v)
        else:
            path = path + '.' + v
    return path.lstrip('.')

def url2path(url):
    '''
    URL('/a/b/c/') to path('a.b.c')
    '''
    return url.strip('/').replace('/', '.')

def path2url(path):
    '''
    path('a.b.c') to URL('/a/b/c/')
    '''
    return '/' + path.replace('.', '/') + '/'

def instance2url(instance):
    qname = instance.qname_()
    url = ''
    for v in qname:
        if isinstance(v, frozendict):
            url += repr(v)
        else:
            url += '/' + v
    url += '/'
    return url

from tega.tree import Cont
def _dict2cont(cont, instance):
    if isinstance(instance, dict):
        for k,v in instance.items():
            version = None
            if isinstance(v, dict):
                _dict2cont(cont[k], v)
            else:
                value = None
                oid = None
                if k.startswith('_'):
                    if k == '_version':
                        version = v
                    elif k == '_value':
                        value = instance['_value']
                else:
                    cont[k] = v
                if value:
                    parent = cont._getattr('_parent')
                    oid = cont._getattr('_oid')
                    parent[oid] = value
                    cont = parent[oid]
                    version = instance['_version']
                if version:
                    cont._setattr('_version', version)
    else:
        parent = cont._parent
        parent[cont._oid] = instance


def dict2cont(dict_):
    '''
    Python dict to Cont
    '''
    root_oid = list(dict_)[0]
    cont = Cont(root_oid)
    _dict2cont(cont, dict_[root_oid])
    return cont

def subtree(path, value):
    '''
    Cont subtree
    '''
    qname = path2qname(path)
    root_oid = qname[0]
    cont = None
    if len(qname) > 1:
        cont = Cont(root_oid)
        if isinstance(value, dict):
            for k in qname[1:]:
                cont = cont[k]
            _dict2cont(cont, value)
        else:
            if len(qname) > 2:
                for k in qname[1:-1]:
                    cont = cont[k]
            k = qname[-1]
            cont[k] = value
            cont = cont[k]
    else:
        cont = Cont(root_oid)
        if isinstance(value, dict):
            _dict2cont(cont, value)
        else:
            raise ValueError('len(qname) <= 1 and its value is not dict')

    return cont

def func_args_kwargs(func_call):
    '''
    Convert a string "func(*args, **kwargs)" into a function name,
    args and kwargs.
    '''
    args = kwargs = None
    f = func_call.rstrip(')').split('(')
    func_path = f[0]
    if len(f) > 1:
        arg = f[1]
        _args = arg.replace(' ', '').split(',')
        _args_ = copy.copy(_args)
        kwargs = {}
        for arg in _args_:
            kv = arg.split('=')
            if len(kv) > 1:
                kwargs[kv[0]] = eval(kv[1])
                _args.remove(arg)
        args = []
        for arg in _args:
            args.append(eval(arg))
    return (func_path, args, kwargs)

def is_func(str_value):
    '''
    Checks if the string is of a RPC instance or not.
    '''
    if str_value.startswith('%') and str_value.endswith('%'):
        return True
    else:
        return False

def newest_commit_log(server_tega_id, dir_):
    '''
    Returns the newest commit log number
    '''
    max_ = 0
    list_ = os.listdir(dir_)
    for n in list_:
        s = n.split('.')
        if s[0] == 'log':
            num = int(s[-1])
            if num > max_:
                max_ = num
    return max_

