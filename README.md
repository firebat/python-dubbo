## Dubbo for Python
try to 

## Demo
1. start java demo server
2. run dubbo.tests.jsonrpc_test.py test jsonrpc


## Java Demo
download zookeeper, modify conf/zoo.cfg like:

    tickTime=2000
    dataDir=/tmp/zookeeper
    clientPort=2181

start

    ./bin/zkServer.sh start


HelloServce.java

    package com.example.dubbo.api;
    
    public interface HelloService {
        String echo(String name);
        int add(int a, int b);
        User getUser(String name);
    }

HelloServiceImpl.java

    package com.example.dubbo.service;

    import com.example.dubbo.api.HelloService;
    import com.example.dubbo.api.User;

    public class HelloServiceImpl implements HelloService {

        public String echo(String name) {
            return "Hello " + name + " from Java";
        }
                    
        public int add(int a, int b) {
            return a + b;
        }
                                        
        public User getUser(String name) {
            User user = new User();
            user.setName(name);
            user.setAge(23);
            return user;
        }
    }

TestServer.java

    package com.example.dubbo.service;
    
    import com.alibaba.dubbo.config.ApplicationConfig;
    import com.alibaba.dubbo.config.ProtocolConfig;
    import com.alibaba.dubbo.config.RegistryConfig;
    import com.alibaba.dubbo.config.ServiceConfig;
    import com.example.dubbo.api.HelloService;
    
    public class TestServer {
    
        public static void main(String[] args) throws InterruptedException {
        
            ServiceConfig<HelloService> service = new ServiceConfig<HelloService>();
            service.setRegistry(new RegistryConfig("zookeeper://localhost:2181"));
            service.setApplication(new ApplicationConfig("hello-app"));
            service.setProtocol(new ProtocolConfig("jsonrpc", 8080)); // for python
            service.setRef(new HelloServiceImpl());
            service.setInterface(HelloService.class);
            service.export();
                                                                
            while (true) {
                // System.out.print(".");
                Thread.sleep(30000);
            }
        }
    }

