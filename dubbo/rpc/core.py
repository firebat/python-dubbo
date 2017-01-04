# -*- coding: utf-8 -*-
import itertools
from dubbo.common import Node


class Protocol(object):

    # 获取缺省端口，当用户没有配置端口时使用
    default_port = 0

    def __init__(self, default_port=None):
        self.default_port = default_port


    def export(self, invoker):
        """
        暴露远程服务
        1. 协议在接收请求时，应记录请求来源方地址信息：RpcContext.getContext().setRemoteAddress()
        2. export()必须是幂等的，也就是暴露同一个URL的Invoker两次，和暴露一次没有区别
        3. export()传入的Invoker由框架实现并传入，协议不需要关心
        :param invoker:
        :return:
        """
        pass


    def refer(self, service_type, url):
        """
        引用远程服务
        1. 当用户调用refer()所返回的Invoker对象的invoke()方法时，协议需相应执行同URL远端export()传入的Invoker对象的invoke()方法
        2. refer()返回的Invoker由协议实现，协议通常需要在此Invoker中发送远程请求
        3. 当url中有设置check=false时，连接失败不能抛出异常，并内部自动恢复
        :param type:
        :param url:
        :return:
        """
        pass


    def destroy(self):
        """
        释放协议
        1. 取消该协议所有已经暴露和引用的服务
        2. 释放协议所占用的所有资源，比如连接和端口
        3. 协议在释放后，依然能暴露和引用新的服务
        :return:
        """
        pass


    @staticmethod
    def service_key(port=0, service_name=None, service_version=None, service_group=None, url=None):
        # port, path, version, group
        group = service_group or url.get_parameter('group')
        version = service_version or url.get_parameter('version')

        group = '{0}/'.format(group) if group else ''
        version = ':{0}'.format(version) if version and version is not '0.0.0' else ''
        return '{0}{1}{2}:{3}'.format(group, service_name or url.path, version, port or url.port)


class Exporter(object):

    invoker = None

    def unexport(self):
        pass


class Invoker(Node):

    # 远程调用类, 与Interface对应
    interface = None

    def invoke(self, invocation):
        pass


class Invocation(object):

    INVOKE_ID = itertools.count()
    invoker = None

    def __init__(self, method_name='', parameter_types=[], arguments=[], attachments={}):
        self.method_name = method_name
        self.parameter_types = parameter_types
        self.arguments = arguments
        self.attachments = attachments
        self.inv_id = Invocation.INVOKE_ID.next()


class Result(object):

    def __init__(self, value=None, exception=None, attachments={}):
        self.value = value
        self.exception = exception
        self.attachments = attachments

    def __str__(self):
        return 'Result [value={0}, exception={1}'.format(self.value, self.exception)
