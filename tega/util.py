from tega.tree import Cont

import copy
import os
import re

def path2qname(path):
    '''
    path('a.b.c') to qname(['a', 'b', 'c'])
    '''
    return path.split('.')

def qname2path(qname):
    '''
    qname(['a', 'b', 'c']) to path('a.b.c')
    '''
    return '.'.join(qname)

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
        url += '/' + v
    url += '/'
    return url

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

def _deserialize(root, dict_):
    for k, v in dict_.items():
        if k.startswith('_'):
            root._setattr(k, v)
        else:
            value = dict_[k]
            if '_value' in value: 
                root[k] = value['_value']
                root[k]._setattr('_version', value['_version'])
            else:
                root[k] = _deserialize(Cont(k), value)
    return root

def deserialize(dict_):
    '''
    Deserializes dict(w/ internal=True option) into Cont
    '''
    root_oid = dict_['_oid']
    root = Cont(root_oid)
    _deserialize(root, dict_)
    return root

_quoted_arg_matcher = re.compile('\s*([\'\"]+[\w\s\.\/-]*[\'\"]+)\s*')

def eval_arg(arg):
    '''
    RPC argument evaluation
    '''
    m = _quoted_arg_matcher.match(arg)
    if m:
        return eval(m.group(1))
    else:
        return eval(arg.strip())

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
        _args = arg.split(',')
        if _args[0] == '':
            _args = []
        _args_ = copy.copy(_args)
        kwargs = {}
        for arg in _args_:
            kv = arg.split('=')
            if len(kv) > 1:
                kwargs[kv[0].strip()] = eval_arg(kv[1])
                _args.remove(arg)
        args = [eval_arg(arg) for arg in _args]
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

