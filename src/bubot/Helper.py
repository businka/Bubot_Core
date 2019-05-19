import os
import json
import copy
from bubot.ExtException import ExtException
# from bubot.Action import Action
from datetime import datetime, timedelta
import asyncio
import inspect


class Helper:
    @classmethod
    def update_dict(cls, base, new):
        for element in new:
            try:
                if element in base:
                    if isinstance(new[element], dict):
                        base[element] = cls.update_dict(base[element], new[element])
                    elif isinstance(new[element], list):
                        for element2 in new[element]:
                            if element2 not in base[element]:
                                base[element].insert(0, element2)
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
                            raise ExtException(e, detail='copy.deepcopy({0})'.format(element))
            except ExtException as e:
                raise ExtException(e, action_name='BubotConfig.update_dict', action_param=element) from e
            except Exception as e:
                raise ExtException('Bad dict', detail='element "{0}": {1}'.format(element, str(e)),
                                   action_name='BubotConfig.update_dict') from e
        return base  # copy.deepcopy(base)

    @classmethod
    def copy(cls, data):
        return copy.deepcopy(data)

    @classmethod
    def compare(cls, base, new):
        def compare_dict(_base, _new):
            pass

        def compare_list(_base, _new):
            pass

        if isinstance(base, dict):
            difference = False
            res = {}
            for elem in new:
                try:
                    if base and elem in base:
                        if isinstance(new[elem], dict):
                            _difference, _res = cls.compare(base[elem], new[elem])
                            if _difference:
                                difference = True
                                res[elem] = copy.deepcopy(_res)
                        else:
                            if new[elem] != base[elem]:
                                difference = True
                                res[elem] = new[elem]
                    else:
                        difference = True
                        res[elem] = new[elem]
                except Exception as e:
                    raise Exception('compare: {0}'.format(str(e)), elem)
        else:
            difference = False
            res = None
            if base != new:
                difference = True
                res = new
        return difference, res

    @classmethod
    def get_class(cls, full_import_name):
        try:
            parts = full_import_name.split('.')
            module = ".".join(parts[:-1])
            m = __import__(module)
            for comp in parts[1:]:
                m = getattr(m, comp)
            return m
        except ImportError as e:
            # ошибки в классе  или нет файла
            raise ImportError('get_class({0}: {1})'.format(full_import_name, str(e)))
        except AttributeError as e:
            # Нет такого класса
            raise AttributeError('get_class({0}: {1})'.format(full_import_name, str(e)))
        except Exception as e:
            # ошибки в классе
            raise ExtException(str(e), detail='get_class({0}: {1})'.format(full_import_name, str(e)))

    @classmethod
    def get_default_config(cls, current_class, root_class, cache):
        _type = root_class.__name__
        try:
            return cache['{0}_{1}'.format(_type, cls.__name__)]
        except KeyError:
            pass
        schema = {}

        for elem in current_class.__bases__:
            if issubclass(elem, root_class):
                try:
                    _schema = cache['{0}_{1}'.format(_type, elem.__name__)]
                except KeyError:
                    _schema = cls.get_default_config(elem, root_class, cache)
                    cache['res' + elem.__name__] = _schema
                Helper.update_dict(schema, _schema)
        if hasattr(current_class, 'file'):
            config_path = '{0}/{1}.json'.format(os.path.dirname(current_class.file), current_class.__name__)
            try:
                with open(config_path, 'r', encoding='utf-8') as file:
                    _schema = json.load(file)
                    Helper.update_dict(schema, _schema)
            except FileNotFoundError:
                return schema
            except Exception as e:
                pass
        cache['{0}_{1}'.format(_type, current_class.__name__)] = schema
        return schema


class ArrayHelper:
    @classmethod
    def update(cls, items, item, field='id'):
        for i in range(len(items)):
            if items[i][field] == item[field]:
                items[i] = item
                return
        items.append(item)

    @classmethod
    def index_list(cls, items, field='id'):
        res = {}
        for index in range(len(items)):
            try:
                res[items[index][field]] = index
            except KeyError:
                pass
        return res

    @classmethod
    def find(cls, items, value, field='id'):
        for i in range(len(items)):
            if items[i][field] == value:
                return i
        return -1


# def load_config(config_type, cache, name=None, user_config=None):
#     if name:
#         base_config, cache = read_buject_config(name, cache)
#         user_config, cache = update_config(config_type, name, base_config, user_config, cache)
#         return user_config, cache
#     else:
#         base_config, cache = read_cache_config(get_path_default_config(config_type), cache)
#         name = config_type
#         base_config, cache = update_config(config_type, name, {}, base_config, cache)
#     return base_config, cache


# def read_config(path):
#     try:
#         with open(path, encoding='utf-8') as config_file:
#             result = config_file.read()
#             result = json.loads(result)
#             return result
#     except Exception as e:
#         raise UserError(str(e), 'BubotConfig.read_config({0}): {1}'.format(path, str(e)))
#
#
# def read_cache_config(path, cache):
#     try:
#         config = cache[path]
#     except KeyError:
#         cache[path] = read_config(path)
#         config = cache[path]
#
#     return copy.deepcopy(config)
#
#
# def read_buject_config(name, cache):
#     _buject = get_class('buject.{0}.{0}.{0}'.format(name))()
#     return read_cache_config(_buject.def_config_path, cache)
#
#
# def get_path_default_config(_config_type):
#     return '{0}{1}.json'.format(os.path.realpath(__file__)[:-15], _config_type)
#
#
# # рекурсивно переопределяем параметры конфига, значаниями из data
# def update_config(config_type, config_name, base_config, new_config, cache):
#     try:
#         parent_name = None
#         parent_config = None
#         try:
#             parent_name = base_config['param']['parent']['value']
#         except KeyError:
#             pass
#         if parent_name:
#             if parent_name.lower() == config_type:
#                 parent_name = config_type
#                 parent_config = read_cache_config(get_path_default_config(config_type), cache)
#             else:
#                 parent_config = read_buject_config(parent_name, cache)
#         else:  # если родитель не указан (это родитель)
#             if config_type != config_name:  # если это ещё не конфиг типа, то берем конфиг типа
#                 parent_name = config_type
#                 parent_config = read_cache_config(get_path_default_config(config_type), cache)
#             else:  # если это ещё не конфиг buject, берем его
#                 if config_name != 'buject':
#                     parent_name = 'buject'
#                     config_type = 'buject'
#                     parent_config = read_cache_config(get_path_default_config(config_type), cache)
#
#         if config_type != config_name and parent_name:
#             base_config = update_config(config_type, parent_name, parent_config, base_config, cache)
#
#         if not base_config:
#             return copy.deepcopy(new_config)
#
#         if new_config:
#             update_dict(base_config, new_config)
#             # for folder in new_config:
#             #     if isinstance(new_config[folder], dict):
#             #         if folder not in base_config:
#             #             base_config[folder] = {}
#             #         else:
#             #             base_config[folder] = update_dict(base_config[folder], new_config[folder])
#             #
#             #     elif isinstance(new_config[folder], list):
#             #         base_config[folder] = copy.deepcopy(new_config[folder])
#             #     else:
#             #         base_config[folder] = new_config[folder]
#         return copy.deepcopy(base_config)
#
#     except BujectError as e:
#         raise BujectError(e, 'update_config({0}, {1})'.format(config_type, config_name))
#     except Exception as e:
#         raise UserError(str(e), 'update_config({0}, {1})'.format(config_type, config_name))


# def update_config(config_type, config_name, base_config, new_config, cache):
#     try:
#         parent_name = None
#         parent_config = None
#
#         if new_config:
#             if 'param' in new_config \
#                     and 'parent' in new_config['param'] \
#                     and new_config['param']['parent']['value']:  # если в новом конфиге указан родитель
#                 parent_name = new_config['param']['parent']['value']
#                 if parent_name.lower() == config_type:
#                     parent_name = config_type
#                     parent_config, cache = read_cache_config(get_path_default_config(config_type), cache)
#                 else:
#                     parent_config, cache = read_buject_config(parent_name, cache)
#         if not parent_name:  # если родитель не указан (это родитель)
#             if config_type != config_name:  # если это ещё не конфиг типа, то берем конфиг типа
#                 parent_name = config_type
#                 parent_config, cache = read_cache_config(get_path_default_config(config_type), cache)
#             # else: # если это ещё не конфиг buject, берем его
#             #     if config_name != 'buject':
#             #         parent_name = 'buject'
#             #         config_type = 'buject'
#             #         parent_config, cache = read_cache_config(get_path_default_config(config_type), cache)
#
#         if config_type != config_name and parent_name:
#             base_config, cache = update_config(config_type, parent_name, parent_config, base_config, cache)
#
#         if not base_config:
#             return copy.deepcopy(new_config), cache
#
#         if new_config:
#             for folder in new_config:
#                 if isinstance(new_config[folder], dict):
#                     if folder not in base_config:
#                         base_config[folder] = {}
#                     # if os.path.exists('./{0}'.format(folder)):  # если данной папки есть свои конфиги, берем их
#                     #     if folder not in base_config:
#                     #         base_config[folder] = {}
#                     #     for element in new_config[folder]:
#                     #         if element not in base_config[folder]:
#                     #             base_config[folder][element] = {}
#                     #         base_config[folder][element], cache = update_config(folder, element,
#                     #                                                             base_config[folder][element],
#                     #                                                             new_config[folder][element], cache)
#                     else:
#                         base_config[folder] = update_dict(base_config[folder], new_config[folder])
#
#                 elif isinstance(new_config[folder], list):
#                     base_config[folder] = copy.deepcopy(new_config[folder])
#                 else:
#                     base_config[folder] = new_config[folder]
#         return base_config, cache
#
#     except BujectError as e:
#         raise BujectError(e, 'update_config({0}, {1})'.format(config_type, config_name))
#     except Exception as e:
#         raise UserError(str(e), 'update_config({0}, {1})'.format(config_type, config_name))


# def copy_dict(config):
#     return copy.deepcopy(config)
#
#
# def config_to_simple_dict(config):
#     result = {}
#     for element in config:
#         if isinstance(config[element], dict):
#             if "value" in config[element]:
#                 result[element] = config[element]["value"]
#             else:
#                 result[element] = config_to_simple_dict(config[element])
#         else:
#             result[element] = config[element]
#     return result
#
#
# def get_buject(buject_name, buject_type="buject"):
#     return get_class('{0}.{1}.{1}.{1}'.format(buject_type, buject_name))


# async def get_redis(host, port, db):
#     try:
#         return await asyncio.wait_for(asyncio_redis.Connection.create(host=host, port=port, db=db), 1)
#     except asyncio.futures.TimeoutError:
#         raise TimeoutError('Redis.Connection({0}:{1}))'.format(host, port, db))
#
#
#
# def get_bubot_config(name, user_config=None):
#     path = "./config/" if os.curdir == "." else ""
#     return get_config(path, name, user_config)
#
#
# def get_default_bubot_config():
#     path = "./engine/" if os.curdir == "." else ""
#     return get_config(path, "default_config")
#
#
# def get_buject_config(name, user_config=None):
#     path = "./buject/" if os.curdir == "." else ""
#     return get_config(path, name, user_config)

#
# def create_user_config(new_bubot_config, available_buject):
#     res = {}
#     for _group in ['param', 'outgoing_event', 'incoming_event', 'incoming_request', 'outgoing_request']:
#         if _group in new_bubot_config:
#             _res = compare_dict(available_buject['Bubot'][_group], new_bubot_config[_group])
#             if _res:
#                 res[_group] = copy.deepcopy(_res)
#
#     if 'depend_buject' in new_bubot_config:
#         res['depend_buject'] = {}
#         for _buject in new_bubot_config['depend_buject']:
#             _depend_buject = new_bubot_config['depend_buject'][_buject]
#             if 'bubot' in _depend_buject:
#                 _depend_buject.pop('bubot')  # убираем параметры бубота из каждого объекта
#             _base_buject = _depend_buject['param']['buject']['value']
#             res['depend_buject'][_buject] = compare_dict(available_buject[_base_buject], _depend_buject)
#             if 'param' not in res['depend_buject'][_buject]:
#                 res['depend_buject'][_buject]['param'] = {}
#             res['depend_buject'][_buject]['param']['buject'] = {'value': _base_buject}
#             # res['depend_buject'][_buject]['param']['name'] = {'value': _depend_buject['param']['name']['value']}
#
#     return res


def convert_ticks_to_datetime(ticks):
    return datetime(1, 1, 1) + timedelta(microseconds=ticks // 10)


def async_test(f):
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        if inspect.iscoroutinefunction(f):
            future = f(*args)
        else:
            coroutine = asyncio.coroutine(f)
            future = coroutine(*args, **kwargs)
        loop.run_until_complete(future)

    return wrapper


