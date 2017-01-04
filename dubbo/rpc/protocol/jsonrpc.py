# coding=utf-8
import random, threading

from jsonrpclib import Server

from dubbo.common import URL
from .. import *
from .abstract import AbstractProtocol, AbstractExporter, AbstractInvoker


class JsonRpcProtocol(AbstractProtocol):

    server_map = {} # xxx.xxx.xxx.xxx:80 => http server

    def __init__(self):
        super(self.__class__, self).__init__(80)
        self.skeleton_map = {} # /com.xxx.xxx.XXXService => ref

    def export(self, invoker):
        url = invoker.url
        uri = self.service_key(url = url)
        exporter = self.exporters.get(uri)

        if not exporter:
            exporter = _JsonRpcExporter(invoker)

            addr = '{0}:{1}'.format(url.ip, url.port)
            server = JsonRpcProtocol.server_map.get(addr)

            if not server:
                # create http server
                ip, port = addr.split(':')
                server = JsonRpcServer((ip, int(port)))
                t = threading.Thread(target=server.serve_forever)
                t.setDaemon(True)
                t.start()
                JsonRpcProtocol.server_map[addr]=server

            # bind uri to server
            server.register_invoker(uri.split(':')[0], invoker)

            # do export
            self.exporters[uri] = exporter

        return exporter


    def refer(self, service_type, url):
        url.protocol = 'http'
        invoker = _JsonRpcInvoker(service_type, url)

        self.invokers.add(invoker)
        return invoker

class _JsonRpcExporter(AbstractExporter):

    def __init__(self, invoker):
        super(self.__class__, self).__init__(invoker)


class _JsonRpcInvoker(AbstractInvoker):

    def __init__(self, interface=None, url=None):
        super(self.__class__, self).__init__(interface, url, keys=('interface', 'group', 'token', 'timeout'))
        # TODO reuse clients
        self.client = Server(url.identity_str)

    def do_invoke(self, invocation):
        invocation.attachments['path'] = self.url.path
        try:
            return Result(self.client._request(invocation.method_name, invocation.arguments))
        except Exception, e:
            return Result(exception = e)


from jsonrpclib.SimpleJSONRPCServer import validate_request, Fault
import SocketServer, SimpleXMLRPCServer
import jsonrpclib, traceback, xmlrpclib, sys, types


class JsonRpcRequestHandler(SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):

    def do_POST(self):
        if not self.path in self.server.invokers:
            self.report_404()
            return

        try:
            max_chunk_size = 10*1024*1024
            size_remaining = int(self.headers["content-length"])
            L = []
            while size_remaining:
                chunk_size = min(size_remaining, max_chunk_size)
                L.append(self.rfile.read(chunk_size))
                size_remaining -= len(L[-1])
            data = ''.join(L)
            response = self.server._marshaled_dispatch(data, self.path)
            self.send_response(200)
        except Exception, e:
            self.send_response(500)
            err_lines = traceback.format_exc().splitlines()
            trace_string = '%s | %s' % (err_lines[-3], err_lines[-1])
            fault = jsonrpclib.Fault(-32603, 'Server error: %s' % trace_string)
            response = fault.response()
        if response == None:
            response = ''
        self.send_header("Content-type", "application/json-rpc")
        self.send_header("Content-length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)
        self.wfile.flush()
        self.connection.shutdown(1)


class JsonRpcServer(SocketServer.TCPServer):

    allow_reuse_address = True

    def __init__(self, server_address, handler_class=JsonRpcRequestHandler, logRequests=True, encoding=None):
        SocketServer.TCPServer.__init__(self, server_address, handler_class)

        self.invokers = {}
        self.logRequests = logRequests
        self.encoding = encoding

    def register_invoker(self, uri, invoker):
        self.invokers['/{}'.format(uri)] = invoker

    def _marshaled_dispatch(self, data, path = None):
        response = None
        try:
            request = jsonrpclib.loads(data)
        except Exception, e:
            fault = Fault(-32700, 'Request %s invalid. (%s)' % (data, e))
            response = fault.response()
            return response
        if not request:
            fault = Fault(-32600, 'Request invalid -- no request data.')
            return fault.response()


        result = validate_request(request)
        if type(result) is Fault:
            return result.response()

        method = request.get('method')
        params = request.get('params')

        try:
            response = self._dispatch(self.invokers[path], method, params)
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            fault = Fault(-32603, '%s:%s' % (exc_type, exc_value))
            return fault.response()
        if 'id' not in request.keys() or request['id'] == None:
            # It's a notification
            return None
        try:
            response = jsonrpclib.dumps(response,
                                        methodresponse=True,
                                        rpcid=request['id']
                                        )
            return response
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            fault = Fault(-32603, '%s:%s' % (exc_type, exc_value))
            return fault.response()


    def _dispatch(self, invoker, method, params):

        if invoker is not None:
            try:
                result = invoker.invoke(Invocation(method_name=method, arguments=params))
                return result.value
            except TypeError:
                return Fault(-32602, 'Invalid parameters.')
            except:
                err_lines = traceback.format_exc().splitlines()
                trace_string = '%s | %s' % (err_lines[-3], err_lines[-1])
                fault = jsonrpclib.Fault(-32603, 'Server error: %s' %
                                         trace_string)
                return fault
        else:
            return Fault(-32601, 'Method %s not supported.' % method)