# coding: utf-8
import threading
import dubbo
from ...constants import SPLIT_COMMA
from ..core import Protocol, Exporter, Invoker
from ..exception import RpcException

class AbstractProtocol(Protocol):

    exporters = {}
    invokers = set()

    def destroy(self):
        """
        释放协议
        1. 取消该协议所有已经暴露和引用的服务
        2. 释放协议所占用的所有资源，比如连接和端口
        3. 协议在释放后，依然能暴露和引用新的服务
        :return:
        """
        for invoker in self.invokers:
            invoker.destroy()
            self.invokers.remove(invoker)

        for path, exporter in self.exporters.items():
            exporter.unexport()
            self.exporters.pop(path)


class AbstractExporter(Exporter):

    lock = threading.RLock()
    unexported = False

    def __init__(self, invoker):
        assert invoker, 'service invoker == null'
        assert invoker.interface, 'service type == null'
        assert invoker.url, 'service url == null'

        self.invoker = invoker

    def unexport(self):
        with self.lock:
            if self.unexported:
                return

            self.unexported = True
            self.invoker.destroy()


    def __str__(self):
        return self.invoker.__str__()


class AbstractInvoker(Invoker):
    """
    远程调用类, 与Interface对应
    """
    def __init__(self, interface=None, url=None, attachment={}, keys=()):
        self.interface = interface
        self.url = url
        self.attachment = attachment if attachment else {
            key: value for key, value in  { key: url.get_parameter(key) for key in keys}.items() if not value
        }

        self.methods = SPLIT_COMMA.split(url.get_parameter('methods', ''))
        self.available = True
        self.destroyed = False

        self.lock = threading.RLock()

    def invoke(self, invocation):
        if self.destroyed:
            raise RpcException('Rpc invoker for service {0} on consumer {1} use dubbo version {2} is DESTROYED, can not be invoked any more!'.format(self.interface, '',  dubbo.version))

        if invocation.method_name not in self.methods:
            raise RpcException('Invalid method name {0}, only support {1}'.format(invocation.method_name, self.methods))

        invocation.invoker = self
        # fill attachment
        return self.do_invoke(invocation)

    def destroy(self):
        with self.lock:
            if self.destroyed:
                return

            self.destroyed = True
            self.available = False

    def do_invoke(self, invocation):
        pass

    def __str__(self):
        return '{0} -> {1}'.format(self.interface, self.url)