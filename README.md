## Dubbo for Python

## Demo
1. start java demo server
2. run dubbo.tests.jsonrpc_test.py test jsonrpc


## zookeeper
download zookeeper, modify conf/zoo.cfg like:

    tickTime=2000
    dataDir=/tmp/zookeeper
    clientPort=2181

start

    ./bin/zkServer.sh start


## java demo
dependencies

    dubbo
    com.101tec:zkclient:0.5   # zookeeper client
    com.ofpay:dubbo-rpc-jsonrpc:1.0.1 # jsonrpc protocol
    com.github.briandilley.jsonrpc4j:jsonrpc4j:1.1 #jsonrpc client
    org.springframework:spring-context

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

start java service using jsonrpc protocol, used to test python dubbo client

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

HelloClient.java
used to test python dubbo service

    package com.example.dubbo.client;
    
    import com.alibaba.dubbo.config.ApplicationConfig;
    import com.alibaba.dubbo.config.ReferenceConfig;
    import com.alibaba.dubbo.config.RegistryConfig;
    import com.example.dubbo.api.HelloService;
    
    public class HelloClient {
    
        public static void main(String[] args) throws InterruptedException {
        
            ReferenceConfig<HelloService> ref = new ReferenceConfig<HelloService>();
            ref.setRegistry(new RegistryConfig("zookeeper://localhost:2181"));
            ref.setApplication(new ApplicationConfig("hello-client"));
            ref.setInterface(HelloService.class);
            ref.setProtocol("jsonrpc");
                                                
            HelloService service = ref.get();
            System.out.println(service.echo("alice"));
            System.out.println(service.add(1, 2));
            System.out.println(service.getUser("bob"));
            int i = 0;
            while (i++ < 1000) {
                Thread.sleep(30000);
            }
            ref.destroy();
        }
    }
