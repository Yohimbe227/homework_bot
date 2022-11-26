class TokenException(Exception):
    def __int__(self, *args):
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        if self.message:
            return f'{self.__name__} {self.message}'
        else:
            return f'{self.__name__} has been raised'


class HTTPError(TokenException):
    def __init__(self, *args):
        super().__init__(self, *args)


class StatusError(TokenException):
    def __init__(self, *args):
        super().__init__(self, *args)


class SendMessageError(TokenException):
    def __init__(self, *args):
        super().__init__(self, *args)
