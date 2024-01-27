"""
TODO Проверка смены IP адреса и автоматическая замена на актуальный

"""

import asyncio
import json
import logging
import os
import re
from json import JSONDecodeError
from typing import TypeVar, Type
from uuid import uuid4

# from .QueueMixin import QueueMixin
from bubot.Ocf.OcfMessage import OcfRequest
from bubot.buject.OcfDevice.subtype.Device.MainLoopMixin import MainLoopMixin
from bubot_helpers.ExtException import ExtException, ExtTimeoutError, NotFound, UserError
from bubot_helpers.Helper import Helper
from bubot import __version__ as device_version

# _logger = logging.getLogger('OcfDevice')
tDevice = TypeVar('tDevice', bound='Device')


class Device(MainLoopMixin):
    scheme = {}
    cache = {}
    file = __file__
    version = device_version
    platform_version = device_version
    template = True

    def __init__(self, **kwargs):
        MainLoopMixin.__init__(self, **kwargs)
        self.loop = kwargs.get('loop', asyncio.get_event_loop())

    @classmethod
    def find_first_config(cls, config_path, class_name):
        _list = os.listdir(config_path)
        pattern = re.compile('{0}.+.json'.format(class_name))
        for _file in _list:
            if os.path.isfile('{0}/{1}'.format(config_path, _file)):
                if pattern.match(_file):
                    return _file.split('.')[1]
        return None

    @classmethod
    def init_from_file(cls, **kwargs):
        kwargs['path'] = os.path.abspath(kwargs.get('path', './'))
        config_dir = cls.get_config_dir(path=kwargs['path'])
        os.makedirs(config_dir, exist_ok=True)

        kwargs['log'] = kwargs['log'] if kwargs.get('log') else logging.getLogger('bubot')
        class_name = kwargs.get('class_name', cls.__name__)
        di = kwargs.get('di')
        config = {}
        if di is None:
            di = cls.find_first_config(config_dir, class_name)
        if di:
            config_path = cls.get_config_path(path=kwargs['path'], device_class_name=class_name, device_id=di)
            try:
                with open(config_path, encoding='utf-8') as file:
                    config = json.load(file)
                    kwargs['log'].info('OcfDevice.init_from_file {0}.{1}'.format(class_name, di))
            except JSONDecodeError as err:
                raise UserError(message='Bad device config file', detail=f'{class_name} {di} {err}')

            except FileNotFoundError:
                kwargs['log'].warning('OcfDevice config not found {0}'.format(config_path))
            except Exception as e:
                raise NotFound(
                    message='Config OcfDevice not found',
                    detail='{0} {1}'.format(str(e), config_path),
                    action='OcfDevice.init_from_config',
                    dump=dict(
                        class_name=class_name,
                        di=di,
                    )
                )
        kwargs['class_name'] = class_name
        kwargs['di'] = di
        return cls.init_from_config(config, **kwargs)

    @classmethod
    def init_from_config(cls, config=None, **kwargs):
        class_name = cls.__name__
        try:
            if config:
                class_name = config['/oic/d']['dmno']
        except KeyError:
            pass
        class_name = kwargs.get('class_name', class_name)
        try:
            _handler = cls.get_device_class(class_name)
            self: Type[tDevice] = _handler(**kwargs)
        except Exception as err:
            raise ExtException(
                message='Bad driver',
                detail=class_name,
                action='OcfDevice.init_from_config',
                parent=err,
                dump=dict(
                    config=config,
                    kwargs=kwargs
                )
            )
        return self.init(config, **kwargs)

    def init(self, config=None, **kwargs):
        try:
            cache = kwargs.get('cache', self.cache)
            _config = self.get_default_config(self.__class__, Device, cache)
            if config:
                Helper.update_dict(_config, config)
            self.resource_layer.init_from_config(_config)
            if not self.get_param('/oic/d', 'piid', None):
                self.set_param('/oic/d', 'piid', str(uuid4()))

            di = self.di
            if not di:
                di = kwargs.get('di')
            self.set_device_id(di)
            self.loop.set_debug(self.log and self.log.level == logging.DEBUG)
            return self
        except Exception as err:
            raise ExtException(
                message='Bad driver config',
                detail=self.__class__.__name__,
                parent=err,
                action='OcfDevice.init_from_config',
                dump=dict(
                    config=config,
                    kwargs=kwargs
                )
            )

    def get_default_config(self, current_class, root_class, cache):
        data = Helper.get_default_config(current_class, root_class, cache)
        data['/oic/d']['dmno'] = current_class.__name__
        data['/oic/d']['sv'] = self.version
        data['/oic/p']['mnpv'] = current_class.platform_version
        return data

    def save_config(self):
        def_data = self.get_default_config(self.__class__, Device, self.cache)
        data = Helper.compare(def_data, self.data)
        try:
            data[1].pop('/oic/mnt')
        except KeyError:
            pass
        try:
            os.mkdir(self.get_config_dir(device=self))
        except FileExistsError:
            pass
        try:
            with open(self.get_config_path(device=self), 'w', encoding='utf-8') as file:
                json.dump(data[1], file, ensure_ascii=False, indent=2)
        except FileNotFoundError:
            return {}
        return data

    async def observe(self, to, callback=None):
        try:
            token = self.coap.token
            msg = OcfRequest(
                to=to,
                fr=self.link,
                op='retrieve',
                token=token,
                mid=self.coap.mid,
                obs=1 if callback is None else 0
            )
            coap_msg, remote = msg.encode_to_coap()
            await self.coap.send_multi_answer_request(coap_msg, remote, callback)
            if callback is None:
                del self.coap.answer[token]
        except TimeoutError as e:
            raise ExtTimeoutError(action='request',
                                  dump=dict(op='observe', to=to)) from None
        except ExtException as e:
            raise ExtException(parent=e,
                               action='{}.request()'.format(self.__class__.__name__),
                               dump=dict(op='observe', to=to)) from None
        except Exception as e:
            raise ExtException(parent=e,
                               action='{}.request()'.format(self.__class__.__name__),
                               dump=dict(op='observe', to=to)) from None

    async def discovery_unowned_devices(self, **kwargs):
        try:
            token = self.coap.token
            result = {}
            msg = OcfRequest(
                to=dict(href='/oic/res'),
                fr=self.link,
                op='retrieve',
                token=token,
                mid=self.coap.mid,
                multicast=True,
                **kwargs
            )
            coap_msg, remote = msg.encode_to_coap()
            if self.coap.ipv6:
                await self.coap.send_multi_answer_request(
                    coap_msg,
                    (self.coap.coap_discovery_ipv6[0], self.coap.multicast_port),
                    self.on_response_oic_res,
                    result
                )
            if self.coap.ipv4:
                await self.coap.send_multi_answer_request(
                    coap_msg,
                    (self.coap.coap_discovery_ipv4[0], self.coap.multicast_port),
                    self.on_response_oic_res,
                    result
                )
            await asyncio.sleep(2)
            result = self.coap.answer[token]['result']
            # del (self.coap.answer[token])
            return result

        except ExtException as e:
            raise Exception(e)
        except Exception as e:
            raise ExtException(e)
