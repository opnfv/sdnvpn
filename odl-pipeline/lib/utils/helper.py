from time import time


def diff_time(time1, time2):
    return int(time1) - int(time2)


def diff_time_to_now(time):
    return int(time.now()) - int(time)


def now():
    return time.now()


def deepcopy(object):
    if isinstance(object, dict):
        new_dict = {}
        for key, value in object.iteritems():
            if isinstance(value, dict) or isinstance(value, list):
                value = deepcopy(value)
            new_dict[key] = value
        return new_dict
    raise Exception('Unknown type %s' % type(object))
