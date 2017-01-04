# coding: utf-8

import os
import threading
import time
import dubbo
import urllib
import socket

from types import FunctionType

from .common import URL
from .constants import *
from .registry.zookeeper import ZookeeperRegistry
from .rpc import *

class _Config(object):

    def __init__(self, **kwargs):
        object_property = dir(self.__class__)
        for key, value in kwargs.items():
            if key in object_property:
                setattr(self, key, value)

    def __str__(self):
        return '<dubbo:{} {} />'.format(self.__class__.__name__.replace('Config', '').lower(), " ".join(k + '="' + str(v) + '"' for k, v in vars(self).iteritems()))


class _Registry(object):

    # 注册中心 URL
    registries = []

    @property
    def registry(self):
        return self.registries[0] if self.registries and len(self.registries) else None

    @registry.setter
    def registry(self, value):
        self.registries = [value]


class MonitorConfig(_Config):

    protocol = None
    address = None
    username = None
    password = None
    group = None
    version = None
    parameters = None


class ModuleConfig(_Config, _Registry):
    # 模块名称
    name = None
    # 模块版本
    version = None
    # 应用负责人
    owner = None
    # 组织名(BU或部门)
    organization = None
    # 服务监控
    monitor = None


class _MethodConfig(_Config):

    # 注册中心请求超时时间(毫秒)
    timeout = None
    # 重试次数
    retries = None
    # 负载均衡
    loadbalance = None
    # 是否异步
    async = None
    #异步发送是否等待发送成功
    send = None
    # 自定义参数
    parameters = {}


class ArgumentConfig(object):
    index = -1
    type = ''
    callback = False

class MethodConfig(_MethodConfig):
    # 方法名
    name = ''
    # 统计参数
    stat = None
    # 是否重试
    retry = None
    # 方法使用线程数限制
    executes = None
    # 是否需要返回
    is_return = None
    arguments = []


class RegistryConfig(_MethodConfig):

    # 注册中心地址
    address = ''
    # 注册中心登录用户名
    username = ''
    # 注册中心登录密码
    password = ''
    # 注册中心缺省端口
    port = 0
    # 注册中心协议
    protocol = ''

    transporter = ''
    server = ''
    client = ''
    cluster = ''
    group = ''
    version = ''

    # 注册中心会话超时时间(毫秒)
    session = 0
    # 动态注册中心列表存储文件
    file = ''
    # 停止时等候完成通知时间
    wait = 0

    # 启动时检查注册中心是否存在
    check = None
    # 在该注册中心上注册是动态的还是静态的服务
    dynamic = None
    # 在该注册中心上服务是否暴露
    registry = None
    # 在该注册中心上服务是否引用
    subscribe = None

    # 是否为缺省
    is_default = None

    def __init__(self, address, **kwargs):
        super(self.__class__, self).__init__(**kwargs)
        self.address = address


class ApplicationConfig(_Config, _Registry):

    # 模块版本
    version = ''
    # 应用负责人
    owner = ''
    # 组织名(BU或部门)
    organization = ''
    # 分层
    architecture = ''
    # 环境，如：dev/test/run
    environment = ''
    # 是否为缺省
    is_default = None

    def __init__(self, name, **kwargs):
        super(self.__class__, self).__init__(**kwargs)
        # 应用名称
        self.name = name


class _Method(object):

    def __init__(self, invoker, method):
        self.invoker = invoker
        self.method = method

    def __call__(self, *args, **kwargs):
        return self.invoker.invoke(Invocation(self.method, arguments=args)).value


class _Ref(object):

    def __init__(self, interface):
        self.interface = interface

    def __getattr__(self, item):
        invokers = ReferenceConfig.service_provides.get(self.interface, None)
        if not invokers:
            raise ValueError('No providers found for interface {0}'.format(self.interface))

        # TODO load balance, valid invokers
        return _Method(invokers[0], item)

    def destroy(self):
        invokers = ReferenceConfig.service_provides.pop(self.interface, None)
        if not invokers:
            return

        for invoker in invokers:
            invoker.destroy()


class _InterfaceConfig(_MethodConfig, _Registry):

    # 集群方式
    cluster = None
    # 过滤器
    filter = None
    # 监听器
    listener = None
    # 负责人
    owner = None
    # 应用信息
    application = None

    def _load_registries(self, provider=False):
        if not self.registries:
            raise ValueError('No such any registry')

        registries = []
        for config in self.registries:
            addresses = config.address or '0.0.0.0'

            if addresses is 'N/A':
                continue

            #map.update({k:v for k, v in vars(self.application).iteritems() if v})
            #map.update({k:v for k, v in vars(config).iteritems() if v})
            defaults={
                'application': self.application.name,
                'path': 'com.alibaba.dubbo.registry.RegistryService',
                'dubbo': dubbo.version,
                'timestamp': int(time.time()*1000),
                'pid': os.getpid(),
                'protocol': 'dubbo',
            }

            urls = [URL.parse_url(address, defaults) for address in SPLIT_SEMI.split(addresses)]
            for url in urls:
                url.parameters['registry'] = url.protocol
                url.protocol = 'registry'

                if (provider and url.get_parameter('registry', True)) or (not provider and url.get_parameter('subscribe', True)):
                    registries.append(url)

        return registries


class _ReferenceConfig(_InterfaceConfig):
    # 检查服务提供者是否存在
    check = None
    # 是否加载时即刻初始化
    init = None
    # 版本
    version = ''
    # 服务分组
    group = ''


class ReferenceConfig(_ReferenceConfig):

    # 接口类型
    interface = ''
    # 客户端类型
    client = ''

    # 方法配置
    methods = []
    # 调用协议
    protocol = ''

    service_provides = {}

    lock = threading.RLock()

    def __init__(self, **kwargs):
        super(self.__class__, self).__init__(**kwargs)

        self.zk = None
        self.ref = None

    def get(self):
        with self.lock:
            if not self.ref:
                self.ref = self._create_ref()

        return self.ref


    def _event_listener(self, event):
        provide_name = event.path[7:event.path.rfind('/')]
        if event.state == 'CONNECTED':
            children = self.zk.get_children(event.path, watch=self._event_listener)
            self._compare_swap_nodes(provide_name, self._unquote(children))
        if event.state == 'DELETED':
            children = self.zk.get_children(event.path, watch=self._event_listener)
            self._compare_swap_nodes(provide_name, self._unquote(children))

    def _unquote(self, origin_nodes):
        return (urllib.unquote(child_node).decode('utf8') for child_node in origin_nodes if child_node)


    def _compare_swap_nodes(self, interface, nodes):

        # clear before refresh
        ReferenceConfig.service_provides.pop(interface, None)

        for child_node in nodes:
            node = urllib.unquote(child_node).decode('utf8')
            url = URL.value_of(node)

            if url.protocol not in PROTOCOL:
                raise ValueError('unsupported protocol {0}'.format(url.protocol))

            invoker = PROTOCOL[url.protocol].refer(interface, url)

            # add node {interface: url}
            # TODO interface | version | group
            if interface not in ReferenceConfig.service_provides:
                ReferenceConfig.service_provides[interface] = [invoker]
            else:
                ReferenceConfig.service_provides[interface].append(invoker)

    def _create_ref(self):
        if not self.interface:
            raise ValueError('<dubbo:reference interface="" /> interface not allow null!')

        if not self.application:
            raise ValueError('No such application config! <dubbo:application name="..." /> required.')

        if not self.registry:
            raise ValueError('registry required')


        registries = self._load_registries()

        # interface, registry => [providers]
        # FIXME refactor
        registry = ZookeeperRegistry(registries[0])
        self.zk = registry.zk
        children = self.zk.get_children('{0}/{1}/{2}'.format('dubbo', self.interface, 'providers'), watch=self._event_listener)
        self._compare_swap_nodes(self.interface, self._unquote(children))

        # register consumer
        ip = self.zk._connection._socket.getsockname()[0]
        parameters = {
            'interface': self.interface,
            'application': self.application.name,
            'category': 'consumer',
            'environment': self.application.environment or 'run',
            'organization': self.application.organization or '',
            'owner': self.application.owner or '',
            'version': self.application.version or '1.0.0',
            'side': 'consumer',
            'dubbo': dubbo.version,
            'timestamp': int(time.time() * 1000),
            'pid': os.getpid(),
        }
        url = 'consumer://{0}/{1}?{2}'.format(ip, self.interface, urllib.urlencode(parameters))
        consumer_path = '{0}/{1}/{2}'.format('dubbo', self.interface, 'consumers')
        self.zk.ensure_path(consumer_path)
        self.zk.create(consumer_path + '/' + urllib.quote(url, safe=''), ephemeral=True)

        # create invoker
        return _Ref(self.interface)

    def destroy(self):
        with self.lock:
            self.ref.destroy()


class ProtocolConfig(_Config):
    # 服务协议
    name = None
    # 服务IP地址(多网卡时使用)
    host = None
    # 服务端口
    port = 0
    # 上下文路径
    context_path = ''
    # 线程池类型
    thread_pool = ''
    # 线程池大小(固定大小)
    threads = 5
    # 最大接收连接数
    accepts = 0
    # 序列化方式
    serialization = ''
    # 字符集
    charset = ''
    # 最大请求数据长度
    payload = 0
    # 心跳间隔
    heartbeat = 5
    # 服务器端实现
    server = ''
    # 客户端实现
    client = ''
    # 支持的telnet命令，多个命令用逗号分隔
    telnet = ''
    # 命令行提示符
    prompt = ''
    # 状态检查
    status = ''
    # 是否注册
    register = None
    # 参数
    parameters = {}
    # 是否为缺省
    is_default = None

    def __init__(self, name, port=0, **kwargs):
        super(self.__class__, self).__init__(**kwargs)
        self.name = name
        self.port = port


class _ServiceConfig(_InterfaceConfig):
    # 服务版本
    version = ''
    # 服务分组
    group = ''
    # 延迟暴露
    delay = None
    # 是否暴露
    export = None
    # 权重
    weight = None
    # 在注册中心上注册成动态的还是静态的服务
    dynamic = None
    # 是否使用令牌
    token = None
    # 访问日志
    accesslog = None
    # 允许执行请求数
    executes = None
    # 有效协议
    protocols = None
    # 是否注册
    register = None

    @property
    def protocol(self):
        return self.protocols[0] if self.protocols and len(self.protocols) else None

    @protocol.setter
    def protocol(self, value):
        self.protocols = [value]

class ProviderConfig(_ServiceConfig):
    # 服务IP地址(多网卡时使用)
    host = None
    # 服务端口
    port = None
    # 上下
    context_path = None
    # 线程池类型
    threadpool = None
    # 线程池大小(固定大小)
    threads = None
    # IO线程池大小(固定大小)
    iothreads = None
    # 线程池队列大小
    queues = None
    # 最大接收连接数
    accepts = None
    # 协议编码
    codec = None
    # 序列化方式
    serialization = None
    # 字符集
    charset = None
    # 最大请求数据长度
    payload = None
    # status检查
    status = None
    # 缓存区大小
    buffer = None
    # 停止时等候时间
    wait = None


class ServiceConfig(_ServiceConfig):
    # 接口类型
    interface = None
    # 接口实现类引用
    ref = None
    # 服务名称
    path = None
    # 方法配置
    methods = []
    # provider config
    provider = None
    urls = []

    lock = threading.RLock()

    zk = None

    def __init__(self):
        self.unexported = False
        self.exported = False
        self.generic = False
        self.exporters = []

    def export(self):

        with self.lock:
            self._do_export()


    def _do_export(self):

        assert not self.unexported, "Already unexported!"
        if self.exported:
            return

        self.exported = True
        assert self.ref, "ref not allow null!"
        assert self.application, "No such application config!"
        assert self.registries, "No such any registry"
        assert self.interface, '<dubbo:reference interface="" /> interface not allow null!'

        self.protocols = self.protocols or [ProtocolConfig(name='dubbo')]
        self.path = self.path or self.interface

        registryURLs = self._load_registries(True)

        # FIXME registryURL => zk mapping
        if not ServiceConfig.zk:
            registry = ZookeeperRegistry(registryURLs[0])
            ServiceConfig.zk = registry.zk

        for protocol in self.protocols:
            self._do_export_protocol_registries(protocol, registryURLs)

    def _do_export_protocol_registries(self, protocol, registryURLs=[]):

        name = protocol.name or 'dubbo'
        host = protocol.host or (self.provider and self.provider.host)
        port = protocol.port or PROTOCOL[protocol.name].default_port

        parameters = {
            'side': 'provider',
            'dubbo': dubbo.version,
            'timestamp': int(time.time()*1000),
            'pid': os.getpid(),
            'application': self.application.name,
            'interface': self.interface,
            'methods': ",".join(self.methods or [x for x,y in self.ref.__class__.__dict__.items() if type(y) == FunctionType])
        }

        if not host or host in ('localhost', '0.0.0.0') or PATTERN_LOCAL_IP.match(host):
            # connect to registry to detective local ip
            parameters['anyhost'] = True
            for url in registryURLs:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    s.connect((url.host, url.port))
                    host = s.getsockname()[0]
                    break
                finally:
                    s.close()

        context_path = protocol.context_path or (self.provider and self.provider.context_path)
        url = URL(name,host=host, port=port, path='{0}/{1}'.format(context_path, self.path) if context_path else self.path, parameters=parameters)

        # startup server in daemon thread
        invoker = proxyFactory.get_invoker(self.ref, self.interface, url)
        exporter = PROTOCOL[url.protocol].export(invoker)

        # export to zookeeper
        client = ServiceConfig.zk
        provider_path = '{0}/{1}/{2}'.format('dubbo', self.interface, 'providers')
        client.ensure_path(provider_path)
        client.create(provider_path + '/' + urllib.quote(str(invoker.url), safe=''), ephemeral=True)

        self.exporters.append(exporter)

    def _check_ref(self):
        assert self.ref, 'ref not allow null!'
        # assert self.ref.__class__.__name__ == self.interface, 'The class {0} unimplemented interface'


class ConsumerConfig(_ReferenceConfig):
    # 是否为缺省
    is_default = None