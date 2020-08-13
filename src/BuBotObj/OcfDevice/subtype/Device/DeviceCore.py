from BuBot.Helpers.Helper import Helper
from BuBot.Helpers.ExtException import ExtException
import asyncio
from BuBot.Core.OcfMessage import OcfResponse, OcfRequest
from BuBot.Core.BuBotHelper import BuBotHelper
from uuid import uuid4
import logging
import random
from BuBot.Core.DeviceLink import DeviceLink, ResourceLink


# self.logger = logging.getLogger('DeviceCore')


class DeviceCore:

    def __init__(self, **kwargs):
        self.log = None
        self.resource = {}
        self.data = {}
        self.coap = None
        self._resource_changed = {}
        self._link = None
        self.loop = None
        self.task = None

    def get_device_id(self):
        return self.data['/oic/d'].get('di')
        # return self.data['/oic/d'].get('piid')

    def set_device_id(self, device_id=None):
        if device_id is None:
            device_id = str(uuid4())
        self.data['/oic/d']['di'] = device_id
        # self.data['/oic/d']['piid'] = device_id

    def get_param(self, uri, *args):
        try:
            _res = self.data[uri]
        except KeyError:
            raise ExtException(
                7003,
                action='OcfDevice.get_param',
                detail='uri:{0}{1}'.format(self.__class__.__name__, uri)
            ) from None
        if not args or args[0] is None:
            return _res
        try:
            return _res[args[0]]
        except KeyError:
            try:
                return args[1]
            except IndexError:
                raise ExtException(
                    7003,
                    action='OcfDevice.get_param',
                    detail='uri:{0}{1} {2}'.format(self.__class__.__name__, uri, args[0])
                ) from None

    def set_param(self, resource, name, new_value, **kwargs):
        try:
            old_value = self.get_param(resource, name, new_value)
            difference, changes = Helper.compare(old_value, new_value)
            if difference:
                self._resource_changed[resource] = True
                self.data[resource][name] = new_value

                if kwargs.get('save_config', False):
                    self.save_config()
        except Exception as e:
            raise ExtException(7000, detail=str(e), dump=dict(
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

    def save_config(self):
        raise NotImplemented()
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

            for elem in self.coap.endpoint:
                if elem == 'multicast' or not self.coap.endpoint[elem]:
                    continue
                eps.append(dict(ep=self.coap.endpoint[elem]['uri']))
            self._link = dict(
                anchor='ocf://{}'.format(self.get_device_id()),
                eps=eps
            )
        if href and href in self.data:
            return dict(
                anchor=self._link['anchor'],
                eps=self._link['eps'],
                href=href

            )
        else:
            return self._link

    async def on_get_request(self, message):
        # interface = message.uri_query['if'][0] if 'if' in message.uri_query else 'oic.if.baseline'
        props = 'on_{0}{1}'.format(message.op, message.to.href.replace('/', '_'))
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
        props = 'on_{0}{1}'.format(message.op, message.to.href.replace('/', '_'))
        if hasattr(self, props):
            logging.debug(props)
            return await getattr(self, props)(message)
        logging.debug('on_post_request')
        return self.update_param(message.to.href, None, message.cn)

    async def on_retrieve_oic_res(self, message):
        device = DeviceLink.init_from_device(self)
        links = []
        for link in device.links:
            if device.links[link].discoverable:
                suited = True
                if message.query:
                    for key in message.query:
                        if not suited:
                            break
                        try:
                            value = getattr(device.links[link], key)
                            if isinstance(value, list):
                                for elem in message.query[key]:
                                    if elem not in value:
                                        suited = False
                                        break
                            elif value not in message.query[key]:
                                suited = False
                        except AttributeError:
                            suited = False
                if suited:
                    links.append(device.links[link].data)
        self.log.debug('discovery {0} links'.format(len(links)))
        await asyncio.sleep(random.random())
        if links:
            return [{
                'di': device.di,
                'n': device.name,
                'links': links
            }]
        raise asyncio.CancelledError

    async def on_response_oic_res(self, message, answer):
        # self.log.debug('begin from {}'.format(message.to.uid))
        async with answer['lock']:
            if answer['result'] is None:
                answer['result'] = {}
            if message.is_successful():
                if message.cn:
                    for device in message.cn:
                        if device['di'] in answer['result']:
                            answer['result'][device['di']].update_from_oic_res(device)
                        else:
                            answer['result'][device['di']] = DeviceLink.init_from_oic_res(device)
            else:
                self.log.error('{0}'.format(message.cn))
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

    def get_install_actions(self):
        return [
            dict(
                id='add_device',
                icon='add_circle',
                title='add device'
            )
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
                raise ExtException(9001, action='notify',
                                   dump=dict(op='observe', to=to)) from None
            except ExtException as e:
                raise ExtException(e,
                                   action='{}.notify()'.format(self.__class__.__name__),
                                   dump=dict(op='observe', to=to)) from None
            except Exception as e:
                raise ExtException(e,
                                   action='{}.notify()'.format(self.__class__.__name__),
                                   dump=dict(op='observe', to=to)) from None

    async def find_devices(self, **kwargs):
        raise NotImplemented()

    @classmethod
    def get_device_class(cls, class_name):
        return BuBotHelper.get_subtype_class('OcfDevice', class_name, folder=True)
