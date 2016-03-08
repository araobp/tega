from collections import MutableMapping
import copy
import io
import json
import uuid

class Cont(MutableMapping):
    '''
    2014/8/14 -- initial version
    2016/3/7  -- wrapped_* classes replaced with Cont sub-classes 

    Classes
    -------
    - Cont and RPC classes 
    - Wrapper classes for Python built-in types

    Tree structure
    --------------
    Cont --+-- Cont --+-- Str(BuiltinTypeMixin, Cont)/str
           |          +-- Int(BuiltinTypeMixin, Cont)/int
           |          +-- Float(BuiltinTypeMixin, Cont)/float
           |          +-- Tuple(BuiltinTypeMixin, Cont)/tuple
           |          +-- Bool(BuiltinTypeMixin, Cont)/bool
           |
           +-- Cont --+-- Cont -- ...
           |          +-- Cont -- ...
           |               :
           |
           +-- Cont --+-- Cont (oid w/ no attributes)
           |
           +-- Cont --+-- RPC/Func

    Note: dict is converted into Cont.
    '''
    
    def __init__(self, _oid=None, _parent=None, _version=0):
        '''
        _oid is a hashable object such as str, int or frozendict.
        '''
        self.__dict__['_oid'] = _oid
        self.__dict__['_parent'] = _parent
        self.__dict__['_version'] = _version
        self.__dict__['_frozen'] = False
        self.__dict__['_ephemeral'] = False

    def __len__(self):
        return len(self.__dict__)
    
    def __setattr__(self, key, value):

        self._immutability_check()
        type_ = type(value)
        if type_ == dict: # dict => Cont conversion
            c = Cont(_oid=key, _parent=self)
            for k,v in value.items():
                c[k] = v
            self.__dict__[key] = c
        elif isinstance(value, Cont):
            self.__dict__[key] = value
            value.__dict__['_parent'] = self
        elif type_ in _builtin_types:
            self.__dict__[key] = _builtin_types[type_](key, self, value)
        elif type_ == Func: # RPC function
            self.__dict__[key] = RPC(key, self, value)
        else:
            raise ValueError('Unidentifed type: {}'.format(type_))

    def __getattr__(self, key):
        self._immutability_check()
        cont = Cont(key, self)
        self.__dict__[key] = cont
        return cont

    def __delattr__(self, key):
        self._immutability_check()
        self.__dict__[key]

    def __getitem__(self, key):
        if key in self.__dict__:
            return self.__dict__[key]
        else:
            return self.__getattr__(key)

    def _extend(self, key):
        if key in self.__dict__:
            return self.__dict__[key]
        else:
            cont = Cont(key, self)
            self.__dict__[key] = cont
            return cont

    __setitem__ = __setattr__
    __delitem__ = __delattr__

    def __call__(self, *args, **kwargs):
        '''
        Creates a list automatically or calls a function attached to
        an instance of RPC class.
        '''
        if isinstance(self, RPC):
            return self._get_func()(*args, **kwargs)
        else:
            raise TypeError

    def freeze_(self):
        '''
        Makes the self Cont object immutable recursively (incl. all the
        children).
        '''
        self.__dict__['_frozen'] = True
        for v in self.values():
            if isinstance(v, Cont):
                v.freeze_()

    def _immutability_check(self):
        '''
        Checks if the self Cont object is immutable.
        '''
        if self.__dict__['_frozen']:
            raise AttributeError()

    def root_(self):
        '''
        Returns a root Cont object.
        '''
        if self._parent:
            return self._parent.root_()
        else:
            return self

    def _qname(self):
        if self._parent:
            yield from self._parent._qname()
        yield self.__dict__['_oid']

    def qname_(self):
        '''
        Returns Qualified Name (QName).
        '''
        return [oid for oid in self._qname()]

    def subtree_(self, path):
        '''
        Gets a subtree on the path from a cont object
        '''
        qname = path.split('.')
        self_ = self
        if len(qname) == 1:
            return self_
        for oid in qname[1:]:
            if oid in self_:
                self_ = self_[oid]
            else:
                raise KeyError
        return self_

    def _deepcopy_parents(self, subtree):
        '''
        "deep" copies the parent nodes.
        '''
        qname = self.qname_()
        if len(qname) > 0:
            parent = self.__dict__['_parent']
            child = subtree
            for cont in reversed(qname[:-1]):
                p = parent.copy_()
                _oid = child.__dict__['_oid']
                p.__dict__[_oid] = child
                child.__dict__['_parent'] = p
        return subtree
    
    def deepcopy_(self, new_parent=None):
        '''
        "deep" copy.
        '''
        _oid = self.__dict__['_oid']
        obj = Cont(_oid, _parent=new_parent)

        # Deepcopies the subtree
        for k,v in self.__dict__.items():
            if k == '_parent' or k == '_frozen':
                pass  # These attributes are set in __init__().
            elif isinstance(v, Cont):
                obj.__dict__[k] = v.deepcopy_(new_parent=obj)
            else:
                obj.__dict__[k] = copy.deepcopy(v)

        # Deepcopies the parents 
        self._deepcopy_parents(obj)

        return obj 

    def copy_(self, freeze=False):
        '''
        "shallow" copy.
        '''
        obj = self.__class__() # Cont
        for k,v in self.__dict__.items():
            obj.__dict__[k] = v
        if freeze:
            obj.__dict__['_frozen'] = True
        return obj

    def __iter__(self):
        '''
        Returs an iterator(generator) excluding hidden keys (_*).
        '''
        for k in self.__dict__:
            if not k.startswith('_'):
                yield k

    def __contains__(self, key):
        '''
        Returs True if key is in __dict__: 
        '''
        return key in self.__dict__

    def items(self):
        '''
        This works like dict.items()
        Caveat: The keyword 'iteritems' cannot be used as an attribute
        for Cont
        '''
        wrapped_types = _wrapped_types
        for k in self:
            if not k.startswith('_'):
                v = self.__dict__[k]
                if type(v) in wrapped_types:
                    yield k, v._value
                else:
                    yield k, v 

    def change_(self, to):
        '''
        This function attaches the node to another parent having the same oid. 
        The old parent keeps the reference to the child even after the change,
        so that the tree can rollback to the previous state in case some trouble
        has happened. 
        '''
        _oid = self.__dict__['_oid']
        self.__dict__['_parent'] = to
        to.__dict__[_oid] = self # The parent makes a link (an attribute) to the object
    
    def __str__(self):
        return self.walk_()

    def ephemeral_(self):
        '''
        Sets the node ephemeral.
        '''
        self.__dict__['_ephemeral'] = True

    def is_ephemeral_(self):
        return self.__dict__['_ephemeral']

    def _is_serializable(self, key):
        #return not key in ('_frozen', '_ephemeral')
        return not key in ('_frozen',)

    def serialize_(self, internal=False, out=None, serialize_ephemeral=True):
        '''
        Serializes a Cont object into Python dict.
        '''
        if out is None:
            out = {}
        for k,v in self.__dict__.items():
            type_v = type(v)
            is_child_or_value = not k.startswith('_')
            if not serialize_ephemeral and is_child_or_value and v.is_ephemeral_():
                continue
            if is_child_or_value:
                if type_v == Cont:
                    out[k] = {}
                elif type_v in _wrapped_types or type_v == RPC:
                    out[k] = v.serialize_(internal=internal)
            elif internal and not is_child_or_value:
                if type_v == Cont or internal and type_v == RPC:
                    s = v.__dict__['_oid']
                    out[k] = s
                elif type_v == Func:
                    out[k] = str(v)
                elif self._is_serializable(k):
                    out[k] = v

            if is_child_or_value and isinstance(v, Cont):
                v.serialize_(internal=internal, out=out[k],
                        serialize_ephemeral=serialize_ephemeral)

            if is_child_or_value and not serialize_ephemeral and not out[k]:
                del out[k]

        return out

    def walk_(self, internal=False):
        '''
        Prints out every attribute in Python dict.
        '''
        return str(self.serialize_(internal=internal))
    
    def dumps_(self, internal=False):
        '''
        Dumps data in JSON format.
        '''
        out = self.serialize_(internal=internal)
        return json.dumps(out)

    def __repr__(self):
        return "'<{} _oid={}>'".format(self.__class__, self.__dict__['_oid'])

    def is_empty_(self):
        _is_empty = True 
        for k in self.__dict__.keys():
            if not k.startswith('_'):
                _is_empty = False
        return _is_empty

    def delete_(self):
        parent = self.__dict__['_parent']
        if parent:
            _oid = self.__dict__['_oid']
            del parent.__dict__[_oid]
        if parent and parent.is_empty_():
            parent.delete_()

class BuiltinTypeMixin(object):
    '''
    Mixin for built-in types
    '''

    def __str__(self):
        return str(self.__dict__['_value'])

    def __repr__(self):
        return repr(self.__dict__['_value'])

    def __eq__(self, v):
        if self.__dict__['_value'] == v:
            return True
        else:
            return False

    def serialize_(self, internal=False, out=None,
            serialize_ephemeral=True):

        if not serialize_ephemeral and self.is_ephemeral_():
            return None
        if out is None:
            out = {}
        if internal:
            for k,v in self.__dict__.items():
                if k == '_value':
                    out[k] = v
                elif k == '_parent':
                    s = v.__dict__['_oid']
                    out[k] = s
                elif self._is_serializable(k):
                    out[k] = v
            return out
        else:
            return self.__dict__['_value']

class Bool(BuiltinTypeMixin, Cont):
    '''
    Bool class.

    Note: bool type cannot be extended.
    '''
    
    def __init__(self, _oid=None, _parent=None, v=False):
        super().__init__(_oid, _parent)
        if v == True or v == False:
            self.__dict__['_value'] = v
        else:
            raise ValueError('Not boolean type')

    def __bool__(self):
        return self.__dict__['_value']

    def deepcopy_(self, new_parent=None):
        _oid = self.__dict__['_oid']
        bool_ = Bool(_oid, _parent=new_parent, v=self.__bool__())
        self._deepcopy_parents(bool_)
        return bool_ 

class Int(BuiltinTypeMixin, Cont):
    '''
    Int class.
    '''
    def __init__(self, _oid=None, _parent=None, v=0):
        super().__init__(_oid, _parent)
        if type(v) == int:
            self.__dict__['_value'] = v
        else:
            raise ValueError('Not int type')

    def deepcopy_(self, new_parent=None):
        _oid = self.__dict__['_oid']
        int_ = Int(_oid, _parent=new_parent, v=self.__dict__['_value'])
        self._deepcopy_parents(int_)
        return int_ 

class Str(BuiltinTypeMixin, Cont):
    '''
    Int class.
    '''
    def __init__(self, _oid=None, _parent=None, v=''):
        super().__init__(_oid, _parent)
        if type(v) == str:
            self.__dict__['_value'] = v
        else:
            raise ValueError('Not int type')

    def deepcopy_(self, new_parent=None):
        _oid = self.__dict__['_oid']
        str_ = Str(_oid, _parent=new_parent, v=self.__dict__['_value'])
        self._deepcopy_parents(str_)
        return str_ 

class Tuple(BuiltinTypeMixin, Cont):
    '''
    Tuple class.
    '''
    def __init__(self, _oid=None, _parent=None, v=[]):
        super().__init__(_oid, _parent)
        type_ = type(v)
        if type_ == tuple:
            self.__dict__['_value'] = v
        elif type_ == list:
            self.__dict__['_value'] = tuple(v)
        else:
            raise ValueError('Neither list or tuple type')

    def deepcopy_(self, new_parent=None):
        _oid = self.__dict__['_oid']
        tuple_ = Tuple(_oid, _parent=new_parent, v=self.__dict__['_value'])
        self._deepcopy_parents(tuple_)
        return tuple_ 

class Float(BuiltinTypeMixin, Cont):
    '''
    Float class.
    '''
    def __init__(self, _oid=None, _parent=None, v=0.0):
        super().__init__(_oid, _parent)
        type_ = type(v)
        if type_ == float:
            self.__dict__['_value'] = v
        else:
            raise ValueError('not float type')

    def deepcopy_(self, new_parent=None):
        _oid = self.__dict__['_oid']
        float_ = Float(_oid, _parent=new_parent, v=self.__dict__['_value'])
        self._deepcopy_parents(float_)
        return float_ 

class RPC(Cont):
    '''
    This class is a wrapper for Func class.
    '''
    
    def __init__(self, _oid=None, _parent=None, v=None):
        super().__init__(_oid, _parent)
        self.__dict__['_value'] = v

    @property
    def owner_id(self):
        return self.__dict__['_value'].owner_id

    def _get_func(self):
        return self.__dict__['_value']

    def __str__(self):
        return str(self.__dict__['_value'])

    def __repr__(self):
        return repr(self.__dict__['_value'])

    def __eq__(self, v):
        if self.__dict__['_value'] == v:
            return True
        else:
            return False

    def serialize_(self, internal=False, out=None,
            serialize_ephemeral=True):

        if not serialize_ephemeral and self.is_ephemeral_():
            return None
        if out is None:
            out = {}
        if internal:
            for k,v in self.__dict__.items():
                if k == '_value':
                    out[k] = str(v)
                elif k == '_parent':
                    s = v.__dict__['_oid']
                    out[k] = s
                elif k != '_frozen':
                    out[k] = v
            return out
        else:
            return self.__str__()

    def deepcopy_(self, new_parent=None):
        _oid = self.__dict__['_oid']
        rpc = RPC(_oid, _parent=new_parent, v=self._get_func())
        self._deepcopy_parents(rpc)
        return rpc 

class Func(object):
    '''
    A function as RPC.
    '''
    def __init__(self, owner_id, func, *args, **kwargs):
        self._owner_id = owner_id
        self.func = func
        self.args = args
        self.kwargs = kwargs

    @property
    def owner_id(self):
        return self._owner_id

    def __str__(self):
        params = []
        for v in self.args:
            if type(v) == str:
                params.append('"{}"'.format(v))
            else:
                params.append(str(v))
        if self.kwargs:
            for k,v in self.kwargs.items():
                if type(v) == str:
                    params.append('{}="{}"'.format(k,v))
                else:
                    params.append('{}={}'.format(k,v))
        if params:
            return '%{}.{}({})'.format(self.owner_id, self.func.__name__,
                    ','.join(params))
        else:
            return '%{}.{}'.format(self.owner_id, self.func.__name__)

    def __call__(self, *args, **kwargs):
        if (self.args or self.kwargs) and (args or kwargs):
            raise ValueError('args/kwargs unaccepted')
        else:
            if self.args:
                args = self.args
            if self.kwargs:
                kwargs = self.kwargs
            if args and kwargs:
                return self.func(*args, **kwargs)
            elif args:
                return self.func(*args)
            elif kwargs:
                return self.func(**kwargs)
            else:
                return self.func()

    def __repr__(self):
        return self.__str__()

    def __eq__(self, obj):
        if self.func == obj:
            return True
        else:
            return False

# Python built-in types
_builtin_types = {list: Tuple, tuple: Tuple, str: Str, int: Int, float: Float,
        bool: Bool}
# Wrapper classes for Python built-in types
_wrapped_types = (Tuple, Str, Int, Float, Bool)
    
