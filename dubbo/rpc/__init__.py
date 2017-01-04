# -*- coding: utf-8 -*-
from .core import *
from .protocol.jsonrpc import *
from .exception import *
from .proxy import *

PROTOCOL = {
    'jsonrpc': JsonRpcProtocol()
}


proxyFactory = ProxyFactory()