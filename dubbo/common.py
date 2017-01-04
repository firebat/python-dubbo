# -*- coding: utf-8 -*-
import socket, urlparse
from dubbo.constants import *

class Node(object):
    url = None
    available = None

    def destroy(self):
        pass


class URL(object):

    def __init__(self, protocol=None, username=None, password=None,  host=None, port=0,  path=None, parameters={}):
        self.protocol = protocol
        self.username = username
        self.password = password
        self.host = host
        self.port = 0 if port < 0 else port
        self.path = path # no '/' prefix
        self.parameters = parameters

        self.ip = socket.gethostbyname(host)

        self._identity_str = None
        self._full_str = None
        self._str_ = None

    @staticmethod
    def value_of(url):
        """
        protocol://username:password@host:port/path?k1=v1&k2=v2
        """
        assert url

        data = urlparse.urlparse(url)
        return URL(data.scheme,
                   data.username,
                   data.password,
                   data.hostname,
                   data.port,
                   data.path[1:] if data.path else '',
                   {key:value for (key, value) in [arg.split('=') for arg in data.query.split('&')]} if data.query else {})

    @staticmethod
    def parse_url(address, defaults={}):
        if not address:
            return None

        url = address if '://' in address else SPLIT_COMMA.split(address)[0]

        u = URL.value_of(url)
        protocol = u.protocol or defaults.get('protocol', 'dubbo')
        username = u.username or defaults.get('username', None)
        password = u.password or defaults.get('password', None)
        host = u.host
        port = u.port or defaults.get('port', 0)
        path = u.path or defaults.get('path', None)
        parameters = defaults.copy()

        for key in ('protocol', 'username', 'password', 'host', 'port', 'path'):
            parameters.pop(key, None)

        return URL(protocol, username, password, host, port, path, parameters)

    @property
    def address(self):
        return self.host if self.port<=0 else '{}:{}'.format(self.host, self.port)

    @property
    def service_interface(self):
        return self.get_parameter('interface', self.path)

    @service_interface.setter
    def service_interface(self, value):
        self.parameters['interface'] = value

    def get_parameter(self, key, default=None):
        value = self.parameters.get(key, None)
        value = value if value else self.parameters.get('default.{0}'.format(key), None)
        return value if value else default

    @property
    def service_key(self):
        if not self.path:
            return None

        group = self.get_parameter('group')
        group = '{0}/'.format(group) if group else ''

        version = self.get_parameter('version')
        version = ':{0}'.format(version) if version else ''

        return ''.join((group, self.path, version))

    @property
    def identity_str(self):
        if not self._identity_str:
            self._identity_str = self.__build_str(True, True, False, False, 'group')
        return self._identity_str

    @property
    def full_str(self):
        if not self._full_str:
            self._full_str = self.__build_str(True, True, False, False)
        return self._full_str

    @property
    def absolute_path(self):
        return '/{0}'.format(self.path) if self.path and self.path[0] != '/' else self.path

    def __build_str(self, append_user = False, append_parameter=False, use_ip = False, use_service = False, *args):
        protocol = '{0}://'.format(self.protocol) if self.protocol else ''
        password = ':{0}'.format(self.password) if append_user and self.username and self.password else ''
        account = '{0}{1}@'.format(self.username, password) if append_user and self.username else ''

        host = self.ip if use_ip else self.host
        port = ':{0}'.format(self.port) if host and self.port > 0 else ''

        path = self.service_key if use_service else self.path
        if path:
            path = '/{0}'.format(path)

        parameters=''
        if append_parameter:
            _args = {key:value for key, value in self.parameters.items() if key in args} if len(args) > 0 else self.parameters
            if len(_args) > 0:
                parameters = '?{0}'.format('&'.join(['{0}={1}'.format(key, value) for key, value in _args.items()]))


        return ''.join((protocol, account, host, port, path, parameters))

    def __service_str(self):
        return self.__build_str(True, False, True, True)

    def __server_str(self):
        # TODO
        return self.__str__()

    def __hash__(self):
        prime = 31
        result = 1
        result = prime * result + (self.host.__hash__() if self.host else 0)
        result = prime * result + (self.parameters.__hash__() if self.parameters else 0)
        result = prime * result + (self.password.__hash__() if self.password else 0)
        result = prime * result + (self.path.__hash__() if self.path else 0)
        result = prime * result + long(self.port)
        result = prime * result + (self.protocol.__hash__() if self.protocol else 0)
        result = prime * result + (self.username.__hash__() if self.username else 0)
        return result

    def __eq__(self, other):

        if self is other:
            return True

        return other is not None\
               and isinstance(other, self.__class__)\
               and self.host == other.host\
               and self.parameters == other.parameters\
               and self.password == other.password\
               and self.path == other.path\
               and self.port == other.port\
               and self.protocol == other.protocol\
               and self.username == other.username

    def __str__(self):
        if not self._str_:
            self._str_ = self.__build_str(False, True, False, False)
        return self._str_


# -*- coding: utf-8 -*-
class Singleton(object):

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)
        return cls._instance
