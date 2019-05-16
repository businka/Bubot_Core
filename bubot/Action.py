from datetime import datetime
import json
from ExtException import ExtException


class Action:
    def __init__(self, name=None, begin=True):
        self.name = name
        self.param = {}
        self.error = None
        self.result = None
        self.begin = None
        self.end = None
        self.time = 0
        self.stat = {}
        if begin:
            self.set_begin()

    def set_begin(self):
        self.begin = datetime.now()

    def set_end(self, result=None):
        self.end = datetime.now()
        if not self.begin:
            self.begin = self.end
        total_time = round((self.end - self.begin).total_seconds(), 2)
        if result is not None:
            self.result = result
        if self.name:
            self.update_stat(self.name, {'count': 1, 'time': total_time - self.time})
        return self

    def add_stat(self, action):
        try:
            for elem in action.stat:
                self.update_stat(elem, action.stat[elem])
            return action.result
        except AttributeError:
            return action

    def update_stat(self, name, stat):
        self.time += stat['time']
        if name not in self.stat:
            self.stat[name] = stat
        else:
            self.stat[name]['count'] += stat['count']
            self.stat[name]['time'] += stat['time']
        pass

    def __bool__(self):
        return False if self.error else True

    def __str__(self):
        pass

    def to_dict(self):
        if self.error:
            return {
                'error': self.error
            }
        else:
            return {
                'result': self.result,
                'stat': self.stat
            }

    def dump(self):
        return json.dumps(self.to_dict(), ensure_ascii=False)
        pass

    def load(self, json_string):
        _tmp = json.loads(json_string)
        self.name = _tmp.get('name')
        self.error = _tmp.get('error', None)
        self.result = _tmp.get('result', None)
        self.begin = _tmp.get('begin', None)
        self.end = _tmp.get('end', None)
        self.time = _tmp.get('time', 0)
        self.stat = _tmp.get('stat', {})
        return self

    def raise_exception(self, error, **kwargs):
        kwargs['action'] = kwargs.get('action', self.name)
        raise ExtException(error, **kwargs)
