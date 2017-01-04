class RpcException(Exception):

    UNKNOWN_EXCEPTION = 0
    NETWORK_EXCEPTION = 1
    TIMEOUT_EXCEPTION = 2
    BIZ_EXCEPTION = 3
    FORBIDDEN_EXCEPTION = 4

    def __init__(self, message='', code=0):
        self.message = message
        self.code = code