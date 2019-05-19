import json
import sys
import traceback


class ExtException(Exception):
    def __init__(self, error, **kwargs):
        self.code = 100
        self.msg = "Класс ошибок получил непредвиденное исключение"
        self.stack = []
        self.data = {}
        self.read_kwargs('action', **kwargs)
        self.read_kwargs('dump', {}, **kwargs)
        if isinstance(error, ExtException):  # прокидываем ошибку наверх
            self.stack += error.stack
            self.stack_add_data()
            self.msg = error.msg
            self.detail = kwargs.get('detail', error.detail)
            self.code = error.code
            self.action = kwargs.get('action', error.action)
            exc_info = sys.exc_info()
            info = traceback.format_exception(*exc_info)
            sys_dump = info[len(info) - 2]
            self.data['dump']['traceback'] = sys_dump
        elif isinstance(error, dict):  # прокидываем ошибку наверх
            self.detail = error['detail']
            self.code = error['code']
            self.dump = error.get('dump', {})
            self.msg = error['message']
            self.action = error['action']
            self.stack = error['stack']
        else:
            self.detail = kwargs.get('detail', '')
            self.action = self.data.get('action', '')
            exc_info = sys.exc_info()
            info = traceback.format_exception(*exc_info)
            self.data['dump']['traceback'] = info[len(info) - 2]
            if isinstance(error, str):
                self.msg = error
                self.code = kwargs.get('code', self.code)
            elif isinstance(error, int):
                self.msg = self.get_msg_by_code(error)
                self.code = error
            elif isinstance(error, Exception):
                self.code = 200
                self.msg = self.get_msg_by_code(self.code)
                self.detail = str(error)
            self.stack_add_data()

    def __str__(self):
        res = '{0}:{1} - {2}'.format(self.code, self.msg, self.detail)
        for elem in self.stack:
            _method = elem.get('action', '')
            _dump = elem.get('dump', '')
            if _method or _dump:
                res += '\n   {}: {}'.format(_method, _dump)
        return res

    def dump(self):
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def to_dict(self):
        return {
            'message': self.msg,
            'code': self.code,
            'detail': self.detail,
            'action': self.action,
            'stack': self.stack
        }

    def stack_add_data(self):
        if self.data.get('action', False) or self.data.get('dump', False):
            self.stack.append(self.data)

    def read_kwargs(self, name, default_value=None, **kwargs):
        try:
            self.data[name] = kwargs[name]
        except KeyError:
            if default_value is not None:
                self.data[name] = default_value

    @staticmethod
    def get_msg_by_code(code):
        # 1ххx - неизвестная фигня
        # 2xxx - ошибки нашей БЛ
        # 3ххx - ошибки чужой БЛ
        # 4ххx - ошибки плагина
        # 5ххx - ошибки клиента
        # 6ххx - ошибки настроек
        # 7ххx - ошибки пользователя
        # 9xxx - ошибки недоступности

        code_errors = {
            1000: "Неизвестная ошибка",
            2000: "Неизвестная ошибка",
            3000: "Неизвестная ошибка",
            6000: "Неизвестная ошибка",
            7000: "Неизвестная ошибка",
            7001: "Не заполнен обязательный параметр",
            7002: "Не найден файл настроек",
            7003: "Параметр не найден",
            7004: "Нефозможно прочитать настроек",
            9001: "Превышено время ожидания ответа",

        }
        return code_errors.get(code, "Неизвестная ошибка нашей БЛ")
