# -*- coding: utf-8 -*-
import threading

from dubbo.common import URL


# RegistryService
# Registry
class Registry:

    # TODO retry
    registered = set()
    subscribed = {}
    notified = {}

    def __init__(self, url):
        self.url = url

        # TODO 本地磁盘缓存文件
        # original = url.get_parameter('file')
        # file = None
        # TODO notify backup urls

    def register(self, url):
        """
        注册数据，比如：提供者地址，消费者地址，路由规则，覆盖规则，等数据。

        注册需处理契约：
        1. 当URL设置了check=false时，注册失败后不报错，在后台定时重试，否则抛出异常。
        2. 当URL设置了dynamic=false参数，则需持久存储，否则，当注册者出现断电等情况异常退出时，需自动删除。
        3. 当URL设置了category=routers时，表示分类存储，缺省类别为providers，可按分类部分通知数据。
        4. 当注册中心重启，网络抖动，不能丢失数据，包括断线自动删除数据。
        5. 允许URI相同但参数不同的URL并存，不能覆盖。

        :param url: 注册信息，不允许为空，如：dubbo://10.20.153.10/com.alibaba.foo.BarService?version=1.0.0&application=kylin
        :return:
        """
        if not url:
            raise  ValueError("register url == null")

        self.registered.add(url)

    def unregister(self, url):
        """
        取消注册.

        取消注册需处理契约：
        1. 如果是dynamic=false的持久存储数据，找不到注册数据，则抛IllegalStateException，否则忽略。
        2. 按全URL匹配取消注册。

        :param url: 注册信息，不允许为空，如：dubbo://10.20.153.10/com.alibaba.foo.BarService?version=1.0.0&application=kylin
        :return:
        """
        self.registered.remove(url)


    def subscribe(self, url, listener=None):
        """
        订阅符合条件的已注册数据，当有注册数据变更时自动推送.

        订阅需处理契约：
        1. 当URL设置了check=false时，订阅失败后不报错，在后台定时重试。
        2. 当URL设置了category=routers，只通知指定分类的数据，多个分类用逗号分隔，并允许星号通配，表示订阅所有分类数据。
        3. 允许以interface,group,version,classifier作为条件查询，如：interface=com.alibaba.foo.BarService&version=1.0.0
        4. 并且查询条件允许星号通配，订阅所有接口的所有分组的所有版本，或：interface=*&group=*&version=*&classifier=*
        5. 当注册中心重启，网络抖动，需自动恢复订阅请求。
        6. 允许URI相同但参数不同的URL并存，不能覆盖。
        7. 必须阻塞订阅过程，等第一次通知完后再返回。

        :param url: 订阅条件，不允许为空，如：consumer://10.20.153.10/com.alibaba.foo.BarService?version=1.0.0&application=kylin
        :param listener: 变更事件监听器，不允许为空
        :return:
        """
        listeners = self.subscribed.get(url, None)
        if not listeners:
            listeners = set()
            self.subscribed[url] = listeners
        listeners.add(listener)


    def unsubscribe(self, url, listener=None):
        """
        取消订阅.

        取消订阅需处理契约：
        1. 如果没有订阅，直接忽略。
        2. 按全URL匹配取消订阅。

        :param url: 订阅条件，不允许为空，如：consumer://10.20.153.10/com.alibaba.foo.BarService?version=1.0.0&application=kylin
        :param listener: 变更事件监听器，不允许为空
        :return:
        """
        listeners = self.subscribed.get(url, None)
        if listeners:
            listeners.remove(listener)

    def lookup(self, url):
        """
        查询符合条件的已注册数据，与订阅的推模式相对应，这里为拉模式，只返回一次结果。

        :param url: 查询条件，不允许为空，如：consumer://10.20.153.10/com.alibaba.foo.BarService?version=1.0.0&application=kylin
        :return: 已注册信息列表，可能为空，含义同{@link com.alibaba.dubbo.registry.NotifyListener#notify(List<URL>)}的参数。
        """
        pass

    def destroy(self):
        pass

# RegistryFactory
# NotifyListener
class RegistryFactory(object):

    # 注册中心获取过程锁
    lock = threading.RLock()

    # 注册中心集合 Map<RegistryAddress, Registry>
    registries = {}

    def get_registry(self, url):
        url.path = 'com.alibaba.dubbo.registry.RegistryService'
        url.parameters['interface'] = 'com.alibaba.dubbo.registry.RegistryService'

        key = url.__service_str()

        while self.lock:
            registry = self.registries.get(key, None)
            if not registry:
                registry = self.__create_proxy(url)
                self.registries[key] = registry
            return registry

    def __create_proxy(self, url):
        return None

    @classmethod
    def destroy_all(cls):
        while cls.lock:
            for registry in cls.registries:
                registry.destroy()
            cls.registries.clear()
