import re
import sys
import random


VERSION = '1.0'


def public(cls_or_method):
    """Marks class or method as public. Only public methods may be accessed through RPC."""
    if not isinstance(cls_or_method, object) and not callable(cls_or_method):
        raise ValueError('public decorator may only be used on classes or methods.')
    setattr(cls_or_method, '__rpc_public__', True)
    return cls_or_method


class _RpcObject(object):
    """
    An object implementing execution of RPC calls.
    """
    def __init__(self, manager, endpoint):
        self._endpoint = endpoint
        self._manager = manager

    def __getattr__(self, method_name):
        return _RpcObject(self._manager, '{}.{}'.format(self._endpoint, method_name))

    def __call__(self, *args, **kwargs):
        message = {
            'rpc': VERSION,
            'id': self._manager._next_uuid(),
            'method': self._endpoint,
            'params': args,
            'params_kw': kwargs
        }
        response = self._manager.send(message)

        if response['rpc'] != VERSION:
            raise ValueError('RPC response version does not match.')

        if response['id'] != message['id']:
            raise ValueError('RPC response id does not match.')

        if 'error' in response:
            raise ValueError(response['error'])

        if 'result' not in response or 'id' not in response:
            raise ValueError('Invalid RPC response.')

        return response['result']


class RpcManager(object):
    def __init__(self):
        self._objects = {}
        self._uuid = random.randint(0, sys.maxsize)

    def register_object(self, name, obj):
        """
        Register object which provides RPC service. Object and it's methods should be decorated with `@public`
        decorator. Raises `ValueError` when any of parameters is incorrect.
        :param name: name at which object is accessible.
        :param obj: object implementing RPC funcionality.
        """
        if re.match(r'^[a-z][a-z0-9_]*$', name, re.IGNORECASE) is None:
            raise ValueError('Endpoint name must be a valid identifier')

        if name in self._objects:
            raise ValueError('Name {} is already registered.'.format(name))

        if not getattr(obj, '__rpc_public__', False):
            raise ValueError('RPC object is not public')

        self._objects[name] = obj

    def unregister_object(self, name):
        """
        Unregister previously registered RPC object. Does not raise exceptions if object was not previously registered.
        :param name: Name of previously registered object.
        """
        if name in self._objects:
            del self._objects[name]

    def get_object(self, name):
        """
        Get a proxy object that may be used to remotely call methods of object registered on remote endpoint. If object
        is not registered on remote endpoint exception will not be thrown from this method, but calling remote methods
        will return error.
        :param name: Name of remote registered object.
        :return: A proxy object for calling it's methods remotely.
        """
        return _RpcObject(self, name)

    def handle(self, message):
        """
        Handle a request from remote endpoint.
        :param message: A python dictionary containing message.
        :return: a python dictionary with response message that should be sent back to remote endpoint.
        """
        response = {
            'rpc': VERSION,
            'id': message['id'],
        }
        parts = message['method'].split('.')

        try:
            obj = self._objects[parts[0]]
        except KeyError:
            obj = None
        else:
            for part in parts[1:]:
                obj = getattr(obj, part)
                if not getattr(obj, '__rpc_public__', False):
                    response['error'] = 'Attribute is not public'

        if 'error' not in response:
            if obj is None:
                response['error'] = 'Attribute does not exist'

            if not callable(obj):
                response['error'] = 'Attribute is not callable'

        if 'error' not in response:
            try:
                response['result'] = obj(*message['params'], **message['params_kw'])
            except Exception as e:
                response['error'] = str(e)

        return response

    def send(self, message):
        """
        Implements sending of messages to remote endpoint.
        :param message: a python dictionary with message contents. It is user's responsibility to encode it.
        :return: Response from remote endpoint. Response should contain same 'id' and 'rpc' values as original message.
        """
        raise NotImplementedError()

    def _next_uuid(self):
        self._uuid *= 16777619
        if self._uuid > sys.maxsize:
            self._uuid = self._uuid & sys.maxsize
        return self._uuid
