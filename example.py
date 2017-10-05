import tinyrpc


@tinyrpc.public
class RpcProviderFoo(object):
    def __init__(self):
        pass

    @tinyrpc.public
    def hello(self, name):
        # RPC calls may raise exceptions and they will be sent over the wire and raised on the other end, as long as
        # your serialization method supports serializing them.
        raise NotImplementedError()


@tinyrpc.public
class RpcProviderBar(object):
    def __init__(self):
        # tinyrpc allows to call rpc methods of member objects if classes creating them are marked as public.
        self.foo = RpcProviderFoo()

    @tinyrpc.public
    def hello(self, name):
        # Ordinary rpc call. Return value may be anything that is serializable by your method of choice.
        return 'Bar greets {}'.format(name)


class MyRpcManagerServer(tinyrpc.RpcManager):
    def send(self, message):
        # This is simplified version of send method. A real implementation would look something like this (pseudocode):
        #   socket.send(serialize(message))
        #   return unserialize(socket.recv())
        # On remote end you should do something like this:
        #   message = unserialize(socket.recv())
        #   response = client.handle(message)
        #   socket.send(serialize(response))
        return client.handle(message)


class MyRpcManagerClient(tinyrpc.RpcManager):
    def send(self, message):
        return server.handle(message)


if __name__ == '__main__':
    server = MyRpcManagerServer()
    server.register_object('bar', RpcProviderBar())

    client = MyRpcManagerClient()
    bar = client.get_object('bar')

    print(bar.hello('rk'))

    try:
        print(bar.foo.hello('rk'))
    except NotImplementedError:
        print('bar.foo.hello raised NotImplementedError()')
