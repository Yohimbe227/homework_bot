from functools import wraps


def only_one(func):
    @wraps(func)
    def wrapper(*args):
        if wrapper.count == 0:
            wrapper.num = func(*args)
            wrapper.count += 1
            return wrapper.num
        return wrapper.num

    wrapper.count = 0
    return wrapper
