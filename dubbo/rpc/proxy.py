from .core import Invoker, Invocation, Result

class ProxyFactory(object):

    def get_invoker(self, proxy, interface, url):
        return ProxyInvoker(proxy, interface, url)

class ProxyInvoker(Invoker):

    def __init__(self, proxy, interface, url):
        assert proxy, 'proxy == null'

        self.proxy = proxy
        self.interface = interface
        self.url = url
        self.available = True

    def invoke(self, invocation):
        return Result(getattr(self.proxy, invocation.method_name)(*invocation.arguments))