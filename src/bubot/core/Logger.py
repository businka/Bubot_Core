# import sys
from multiprocessing import Lock


class Logger:
    CRITICAL = 50
    ERROR = 40
    WARNING = 30
    INFO = 20
    DEBUG = 10
    NOTSET = 0
    _levels = {
        0: 'NOTSET',
        10: 'DEBUG',
        20: 'INFO',
        30: 'WARNING',
        40: 'ERROR',
        50: 'CRITICAL'
    }

    def __init__(self, device, **kwargs):
        log = kwargs.get('log')
        if log:
            self.lock = log.lock
        else:
            self.lock = Lock()
        self._level = None
        self._level_name = None
        self.device = device
        self.level = kwargs.get('level', 'error')
        self.format = kwargs.get(
            'format',
            '%(levelname)s %(name)s %(funcName)s %(message)s'
        )
        # if not device or not log or isinstance(self.device, multiprocessing.Process):
        #     self.logger = multiprocessing.get_logger()
        # else:
        #     self.logger = log.logger
        self.name = kwargs.get('name', device.__class__.__name__)

    def debug(self, msg, *args, **kwargs):
        self.log(10, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.log(20, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.log(30, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.log(40, msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.log(50, msg, *args, **kwargs)

    def log(self, level, msg, *args, **kwargs):
        if level >= self._level:
            level_name = self._levels[level]
            self.lock.acquire()
            try:
                msg = self.format % dict(levelname=level_name, name=self.name, message=msg, funcName='')
                print(msg)
                # self.logger.log(level, message)
            finally:
                self.lock.release()

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, value):
        self._level = getattr(self, value.upper())
        self._level_name = value.upper()
