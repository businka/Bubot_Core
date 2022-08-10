import asyncio
import logging
import os.path
from uuid import uuid4

from Bubot.Core.BubotHelper import BubotHelper
from Bubot.Core.DeviceLink import ResourceLink
from Bubot.Core.OcfMessage import OcfResponse, OcfRequest
from Bubot.Helpers.ExtException import ExtException, KeyNotFound
from Bubot.Helpers.Helper import Helper
from Bubot.Ocf.ResourceLayer import ResourceLayer
from Bubot.Ocf.TransporLayer import TransportLayer


# self.logger = logging.getLogger('DeviceCore')


class DeviceCore:

    def __init__(self, **kwargs):
        self.res = {}
        self.transport_layer = TransportLayer(self)
        self.resource_layer = ResourceLayer(self)

        self.log = None
        self.coap = None
        self._resource_changed = {}
        self._link = None
        self.loop = None
        self.task = None
        self.path = os.path.abspath(kwargs.get('path', './'))

    @property
    def data(self):
        result = {}
        for href in self.res:
            result[href] = self.res[href].data
        return result

    def get_device_id(self):
        return self.res['/oic/d'].get_attr('di', None)

    def get_device_name(self):
        try:
            return self.res['/oic/d'].get_attr('n')
        except Exception:
            return self.__class__.__name__

    def set_device_id(self, device_id=None):
        if device_id is None:
            device_id = str(uuid4())
        self.res['/oic/d'].set_attr('di', device_id)
        self.res['/oic/sec/doxm'].set_attr('deviceuuid', device_id)

    def get_param(self, href, *args):
        try:
            _res = self.res[href].data
        except KeyError:
            raise KeyNotFound(
                action='OcfDevice.get_param',
                detail=f'{href} ({self.__class__.__name__})'
            ) from None
        if not args or args[0] is None:
            return _res
        try:
            return self.res[href].get_attr(*args)
        except KeyError:
            try:
                return args[1]
            except IndexError:
                raise KeyNotFound(
                    action='OcfDevice.get_param',
                    detail=f'{args[0]} ({self.__class__.__name__}{href})'
                ) from None

    def set_param(self, resource, name, new_value, *, save_config=False, **kwargs):
        try:
            old_value = self.get_param(resource, name, None)
            difference, changes = Helper.compare(old_value, new_value)
            if difference:
                self._resource_changed[resource] = True
                self.data[resource][name] = new_value

                if save_config:
                    self.save_config()
        except Exception as e:
            raise ExtException(detail=str(e), dump=dict(
                resource=resource,
                name=name,
                value=new_value
            ))

    def update_param(self, resource, name, new_value, **kwargs):
        old_value = self.get_param(resource, name)
        difference, changes = Helper.compare(old_value, new_value)
        if difference:
            self._resource_changed[resource] = True
            if isinstance(old_value, dict):
                Helper.update_dict(old_value, changes)
            elif isinstance(old_value, (str, int, float, bool)):
                self.data[resource][name] = changes
            elif isinstance(old_value, list):
                self.log.warning("NOT SUPPORTED OPERATIONS!!!")
                self.data[resource][name] = changes

            if kwargs.get('save_config', False):
                self.save_config()
        return changes

    def on_update_oic_con(self, message):
        changes = self.update_param(message.to.href, None, message.cn)
        if 'log_level' in changes:
            self.log.setLevel(getattr(logging, self.get_param('/oic/con', 'logLevel', 'error').upper()))
        return changes

    def get_config_path(self):
        return os.path.join(self.path, f'{self.__class__.__name__}.{self.get_device_id()}.json')

    def delete_config(self):
        os.remove(self.get_config_path())

    def save_config(self):
        raise NotImplementedError()
        # listener = self.listener.get(name, [])
        # task = []
        # for device in listener:
        #     task.append(self.send_event_change(name, device))
        # await asyncio.gather(task)

    async def send_event_change(self, resource_name, receiver):
        pass

    @property
    def link(self):
        return self.get_link()

    def get_link(self, href=None):
        if self._link is None:
            eps = []
            if not self.transport_layer.coap:
                raise KeyNotFound(detail='COAP socket not found')
            # for elem in self.coap.endpoint:
            #     if elem == 'multicast' or not self.coap.endpoint[elem]:
            #         continue
            #     eps.append(dict(ep=self.coap.endpoint[elem]['uri']))
            self._link = dict(
                anchor='ocf://{}'.format(self.get_device_id()),
                eps=self.transport_layer.get_eps()
            )
        if href and href in self.data:
            return dict(
                anchor=self._link['anchor'],
                eps=self._link['eps'],
                href=href
            )
        else:
            return self._link

    def change_provisioning_state(self, new_state=None):
        provisioning_state = self.get_param('/oic/sec/pstat')
        if not provisioning_state['dos']:  # начальная инициализация
            provisioning_state['dos'] = {
                "s": 0,
            }
            # self.set_device_id(str(uuid4()))
            self.res['/oic/sec/doxm'].set_attr('devowneruuid', "00000000-0000-0000-0000-000000000000")
            self.res['/oic/sec/doxm'].set_attr('rowneruuid', "00000000-0000-0000-0000-000000000000")

    async def on_get_request(self, message):
        # interface = message.uri_query['if'][0] if 'if' in message.uri_query else 'oic.if.baseline'
        self.log.debug(f'on_{message.op} {message.to.href}')
        props = f'on_{message.op}{message.to.href.replace("/", "_")}'
        if message.obs is not None:  # observe request
            if message.obs == 1:  # cancel observer
                self.del_listener(message.to.href, message.fr.uid)
            elif message.obs == 0:  # observe request
                self.add_listener(message.to.href, message.fr, message.token)
                pass
        if hasattr(self, props):
            return await getattr(self, props)(message)
        return self.get_param(message.to.href)

    async def on_post_request(self, message):
        # interface = message.uri_query['if'][0] if 'if' in message.uri_query else 'oic.if.baseline'
        self.log.debug(f'on_{message.op} {message.to.href}')
        props = 'on_{0}{1}'.format(message.op, message.to.href.replace('/', '_'))
        if hasattr(self, props):
            logging.debug(props)
            return await getattr(self, props)(message)
        logging.debug('on_post_request')
        return self.update_param(message.to.href, None, message.cn)

    # async def on_response_oic_res(self, message, answer):
    #     # self.log.debug('begin from {}'.format(message.to.uid))
    #     async with answer['lock']:
    #         if answer['result'] is None:
    #             answer['result'] = {}
    #         if message.is_successful():
    #             if message.cn:
    #                 for device in message.cn:
    #                     if device['di'] in answer['result']:
    #                         answer['result'][device['di']].update_from_oic_res(device)
    #                     else:
    #                         answer['result'][device['di']] = DeviceLink.init_from_oic_res(device)
    #         else:
    #             self.log.error('{0}'.format(message.cn))
    # self.log.debug('end from {}'.format(message.to.uid))

    async def on_update_oic_mnt(self, message):
        result = self.update_param(message.to.href, None, message.cn)
        state = message.cn.get('currentMachineState')
        if state:
            if state == 'cancelled':
                self.loop.create_task(self.cancel())

    async def cancel(self):
        self.log.debug('begin cancelled')
        self.set_param('/oic/mnt', 'currentMachineState', 'cancelled')
        try:
            # await self.task
            await asyncio.wait_for(self.task, 30)
        except asyncio.TimeoutError:
            self.task.cancel()

    def get_discover_res(self):
        result = {}
        for href in self.data:
            try:
                if self.data[href]['p']['bm'] == 0:
                    continue
                result[href] = self.data[href]
            except:
                result[href] = self.data[href]
        return result

    @classmethod
    def get_install_search_action(cls):
        return dict(
            name='CallDataSourceForSelectedItems',
            icon='mdi-radar',
            title='search OcfDriver',
            data={
                "method": "find_devices",
                "operation": {
                    "title": "Find devices",
                    "cancelable": True,
                    "show": True,
                    "formUid": "OcfDriver/FoundDevices"
                },
                "dataSource": {
                    "type": "Vuex",
                    "storeName": "LongOperations",
                    "dispatchName": "run",
                    "keyProperty": "id",
                    "objName": "OcfDriver"
                }
            }
        )

    @classmethod
    def get_install_actions(cls):
        return [
            # dict(
            #     name='CallDataSourceForSelectedItems',
            #     icon='mdi-plus-circle-outline',
            #     title='add devices',
            #     data=dict(
            #         method='add_devices'
            #     )
            # )
        ]

    def add_listener(self, href, link, token):
        listening = self.get_param('/oic/con', 'listening')
        for elem in listening:
            if elem['href'] == href and elem['di'] == link['di']:
                return
        listening.append(dict(
            href=href,
            di=link.di,
            ep=link.get_endpoint(),
            token=token
        ))
        self.set_param('/oic/con', 'listening', listening)

    def del_listener(self, href, di):
        listening = self.get_param('/oic/con', 'listening')
        change = False
        for i, elem in enumerate(listening):
            if elem['href'] == href and elem['di'] == di:
                del listening[i]
                change = True
                break
        if change:
            self.set_param('/oic/con', 'listening', listening)

    async def check_changes(self):
        if self._resource_changed:
            for href in self._resource_changed:
                if self._resource_changed[href]:
                    self._resource_changed[href] = False
                    await self.notify(href, self.get_param(href))

    async def notify(self, href, data):  # send notify response to observer
        listening = self.get_param('/oic/con', 'listening')
        if not listening:
            return
        to = ResourceLink.init_from_link(self.link)
        to.href = href
        for elem in listening:
            if elem['href'] != href:
                continue
            try:
                self.log.debug('notify {0} {1}'.format(self.get_device_id(), href))
                msg = OcfResponse.generate_answer(data, OcfRequest(
                    to=to,
                    fr=ResourceLink.init_from_link(dict(di=elem['di'], ep=elem['ep'])),
                    op='retrieve',
                    token=elem['token'],
                    mid=self.coap.mid,
                    obs=0
                ))
                await self.coap.send_answer(msg)
            except TimeoutError as e:
                raise Exception(9001, action='notify',
                                dump=dict(op='observe', to=to)) from None
            except ExtException as e:
                raise ExtException(parent=e,
                                   action='{}.notify()'.format(self.__class__.__name__),
                                   dump=dict(op='observe', to=to)) from None
            except Exception as e:
                raise ExtException(parent=e,
                                   action='{}.notify()'.format(self.__class__.__name__),
                                   dump=dict(op='observe', to=to)) from None

    async def find_devices(self, **kwargs):
        raise NotImplementedError()

    def add_route(self, app):
        raise NotImplementedError()

    @classmethod
    def get_device_class(cls, class_name):
        return BubotHelper.get_subtype_class('OcfDevice', class_name, folder=True)
