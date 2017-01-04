import unittest

from tests.service import HelloService

from dubbo.config import *
from dubbo.rpc import Invocation
from dubbo.rpc.protocol.jsonrpc import JsonRpcProtocol

class HelloService:

    def echo(self, name):
        return 'hello {}'.format(name)

    def add(self, x, y):
        return x + y

    def getUser(self, name):
        return {
            'name': name,
            'age': 17
        }

class TestDubbo(unittest.TestCase):

    def test_ref_direct(self):
        protocol = JsonRpcProtocol()
        url = URL.value_of('jsonrpc://localhost:8080/com.example.dubbo.api.HelloService?anyhost=true&application=hello-app&dubbo=3.1.5&interface=com.example.dubbo.HelloService&methods=add,echo,getUser&pid=21809&side=provider&timestamp=1434094361954')

        invoker = protocol.refer('com.demo.HelloService', url)

        def run(invocation):
            value = invoker.invoke(invocation).value
            print type(value), value

        run(Invocation('echo', arguments=['alice']))
        run(Invocation('add', arguments=[1, 2]))
        run(Invocation('getUser', arguments=['bob']))


    def test_ref_zk(self):
        ref = ReferenceConfig()
        ref.registry = RegistryConfig('zookeeper://localhost:2181')
        ref.application = ApplicationConfig('hello_client_py')
        ref.interface = 'com.example.dubbo.api.HelloService'
        ref.protocol = 'jsonrpc'

        service = ref.get()

        print service.echo('alice')
        print service.add(1, 2)
        print service.getUser('jack')

        ref.destroy()


    def test_srv_direct(self):
        from dubbo.rpc.protocol.jsonrpc import JsonRpcServer

        server = JsonRpcServer(('localhost', 8080))
        server.register_invoker('com.example.dubbo.api.HelloService', ProxyInvoker(HelloService()))
        # server.serve_forever()


    def test_srv_zk(self):

        service = ServiceConfig()
        service.registry = RegistryConfig('zookeeper://localhost:2181')
        service.application = ApplicationConfig('hello_server_py')
        service.protocol = ProtocolConfig('jsonrpc', 8080)
        service.ref = HelloService()
        service.interface = 'com.example.dubbo.api.HelloService'
        service.export()

        import time
        while True:
            time.sleep(5)
