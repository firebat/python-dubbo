# -*- coding: utf-8 -*-
import threading, urllib

from kazoo.client import KazooClient
from kazoo.protocol.states import KazooState

from dubbo.common import URL

class ZookeeperRegistry(object):

    _connect_state = 'UNCONNECT'

    registered = set()

    def __init__(self, url):
        self.url = url

        group = url.get_parameter('group', 'dubbo')
        if not group.startswith('/'):
            group = '/{0}'.format(group)

        self.root = group

        # 连接超时 1min
        self.zk = KazooClient(hosts = url.address)
        self.zk.add_listener(self.__state_listener)
        self.zk.start()

    def __state_listener(self, state):

        if state == KazooState.LOST:
            # Register somewhere that the session was lost
            self._connect_state = state
        elif state == KazooState.SUSPENDED:
            # Handle being disconnected from Zookeeper
            # print 'disconnect from zookeeper'
            self._connect_state = state
        else:
            # Handle being connected/reconnected to Zookeeper
            # print 'connected'
            self._connect_state = state


    def register(self, url):
        # consumer://
        self.zk.create(self.__to_url_path(url), ephemeral=url.get_parameter('dynamic', True))

    def unregister(self, url):
        self.zk.delete(self.__to_url_path(url))

    def lookup(self, url):
        assert url is not None
        pass

    def destroy(self):
        self.zk.stop()

    def __to_root_dir(self):
        return '/' if self.root is '/' else '{0}/'.format(self.root)

    def __to_root_path(self):
        return self.root

    def __to_service_path(self, url):
        name = url.service_interface
        return self.__to_root_path() if name is '*' else self.__to_root_dir() + urllib.quote(name)

    def __to_category_path(self, url):
        return '{0}/{1}'.format(self.__to_service_path(url), url.get_parameter('category', 'providers'))

    def __to_url_path(self, url):
        return '{0}/{1}'.format(self.__to_category_path(url), urllib.quote_plus(url.full_str))

    def __to_categories_path(self, url):
        categories = ['providers', 'consumers', 'routers', 'configurators'] if url.get_parameter('category') is '*'\
            else url.get_parameter('category', ['providers'])

        service_path = self.__to_service_path(url)
        return ['{0}/{1}'.format(service_path, category) for category in categories]

if __name__ == '__main__':
    url = URL('zookeeper', host='localhost', port=2181)
    registry = ZookeeperRegistry(url)

    consumer = URL.value_of('consumer://192.168.112.129/com.example.dubbo.HelloService?active=false&application=hello-client&category=consumers&check=false&connected=true&dubbo=3.1.5&interface=com.example.dubbo.HelloService&methods=getUser,add,echo&pid=16628&protocol=jsonrpc&side=consumer&timestamp=1434444363164')
    registry.register(consumer)
    registry.unregister(consumer)

    registry.destroy()