import copy
from datetime import datetime, timedelta
from ExtException import ExtException


class Helper:
    @staticmethod
    def get_class(class_full_path):
        try:
            parts = class_full_path.split('.')
            module = ".".join(parts[:-1])
            m = __import__(module)
            for comp in parts[1:]:
                m = getattr(m, comp)
            return m
        except ImportError as e:
            # ошибки в классе  или нет файла
            raise ImportError('get_class({0}: {1})'.format(class_full_path, str(e)))
        except AttributeError as e:
            # Нет такого класса
            raise AttributeError('get_class({0}: {1})'.format(class_full_path, str(e)))
        except Exception as e:
            # ошибки в классе
            raise Exception('get_class({0}: {1})'.format(class_full_path, str(e)))

    @staticmethod
    def convert_ticks_to_datetime(ticks):
        return datetime(1, 1, 1) + timedelta(microseconds=ticks // 10)

    @staticmethod
    def update_dict(base, new):
        if not new:
            return base
        for element in new:
            try:
                if element in base:
                    if isinstance(new[element], dict):
                        base[element] = Helper.update_dict(base[element], new[element])
                    elif isinstance(new[element], list):
                        base[element] = copy.deepcopy(new[element])
                    else:
                        base[element] = new[element]
                else:
                    try:
                        base[element] = copy.deepcopy(new[element])
                    except TypeError as e:
                        if not base:
                            base = {
                                element: copy.deepcopy(new[element])
                            }
                        else:
                            raise Exception('Непредвиденная ситуация при ')
            except ExtException as e:
                try:
                    _elem = '{0}.{1}'.format(element, e.stack[len(e.stack)-1]['dump']['element'])
                    _msg = e.stack[0]['dump']['msg']
                except ExtException:
                    _msg = str(e)
                    _elem = element
                raise ExtException(
                    e,
                    action='Helper.update_dict',
                    detail='{1} - {0}'.format(_msg, _elem),
                    dump={
                        'element': _elem})
            except Exception as e:
                raise ExtException(
                    605,
                    action='Helper.update_dict',
                    detail='{0}({1})'.format(e, element),
                    dump={
                        'element': element,
                        'msg': str(e)
                    })
        return base


def get_class(kls):
    try:
        parts = kls.split('.')
        _module = ".".join(parts[:-1])
        m = __import__(_module)
        for comp in parts[1:]:
            m = getattr(m, comp)
        return m
    except ImportError as e:
        # ошибки в классе  или нет файла
        raise ImportError('get_object_class({0}: {1})'.format(kls, str(e)))
    except AttributeError as e:
        # Нет такого класса
        raise AttributeError('get_object_class({0}: {1})'.format(kls, str(e)))
    except Exception as e:
        # ошибки в классе
        pass
        # raise Error(str(e), 'get_object_class({0}: {1})'.format(kls, str(e)))

