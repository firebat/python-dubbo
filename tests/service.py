class HelloService(object):

    def __init__(self):
        pass

    def echo(self, name):
        return 'Hello {0} from python'.format(name)

    def add(self, a, b):
        return a + b

    def getUser(self, name):
        return {'name': name, 'age': 25}


if __name__ == '__main__':

    ref = HelloService()
    print ref.echo('alice')