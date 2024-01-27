# from bubot.core.Coap.coap import Message
from uuid import uuid4

from bubot_helpers.ExtException import ExtException
from .ResourceLink import ResourceLink
from ..buject.OcfDevice.subtype.Device.Device import Device


# _logger = logging.getLogger(__name__)


class DeviceLink:
    def __init__(self, data=None):
        self.links = {}
        self.data = {} if data is None else data
        # self.di = None
        # self.n = None
        # self.eps = None

    @property
    def di(self):
        return self.data.get('di')

    @property
    def eps(self):
        return self.data.get('eps')

    @property
    def n(self):
        return self.data.get('n')

    async def add_to_cloud(self, sender_device, user, cis='coap+tcp://192.168.1.11:8777'):
        try:
            disposable_access_token = str(uuid4())
            sender_device.log.info(f'{self.di} register access token {disposable_access_token}')
            await user.update_auth({'type': 'ocf_reg_device', 'id': self.di, 'value': disposable_access_token})
            await self.device_ownership(sender_device, user.obj_id, new_di=self.di,
                                        cis=cis, sid=disposable_access_token)
        except Exception as err:
            raise ExtException(parent=err)

    # @classmethod
    # def get_default_link(cls):
    #     return {
    #         'di': '',  # device id
    #         'n': '',
    #         'eps': []
    #     }

    # @classmethod
    # def get_resource_by_uri(cls, resources, uri):
    #     link = ResourceLink.init_from_uri(uri)
    #     if not link.di:
    #         raise ExtException(message='bad schema id, need ocf')
    #     try:
    #         return resources[link.di].links[link.href]
    #     except KeyError:
    #         raise ExtException(message='resource not found', detail=uri)
    #
    # @classmethod
    # def init_from_oic_res(cls, data):
    #     self = cls()
    #     self.di = data['di']
    #     # self.n = data.get('n', '')
    #     for link in data['links']:
    #         data = ResourceLink.init_from_link(link, di=self.di)
    #         self.links[data.get('href')] = data
    #         self.eps = data.data['eps']
    #     return self
    #
    # @classmethod
    # def init_from_doxm_msg(cls, msg):
    #     self = cls()
    #     data = msg.decode_payload()
    #     self.di = data['deviceuuid']
    #     for link in data['links']:
    #         data = ResourceLink.init_from_link(data, di=self.di)
    #         self.links[data.get('href')] = data
    #         self.eps = data.data['eps']
    #     return self
    #
    # def update_from_oic_res(self, data):
    #     raise NotImplementedError()
    #
    # async def retrieve(self, sender_device, link):
    #     _data = self.links[link].retrieve(sender_device)
    #     return _data
    #
    # async def retrieve_all(self, sender_device):
    #     requests = []
    #     index = []
    #     result = []
    #     for href in self.links:
    #         if href == '/oic/res':
    #             continue
    #         index.append(href)
    #         requests.append(self.links[href].retrieve(sender_device))
    #     result = await asyncio.gather(*requests, return_exceptions=True, loop=sender_device.loop)
    #     for i in range(len(result)):
    #         if not isinstance(result[i], Exception):
    #             self.data[index[i]] = result[i]
    #     pass
    #
    # @classmethod
    # def init_from_device(cls, device):
    #     self = cls()
    #     self.data = device.data
    #     self.di = device.di
    #     self.eps = self.get_device_eps(device)
    #     for res in self.data:
    #         self.links[res] = ResourceLink.init_from_device(self, res)
    #     return self
    #
    # @staticmethod
    # def get_device_eps(device):
    #     eps = []
    #     if device.coap and device.coap.endpoint:
    #         for elem in device.coap.endpoint:
    #             if elem == 'multicast' or not device.coap.endpoint[elem]:
    #                 continue
    #             eps.append(dict(ep=device.coap.endpoint[elem]['uri']))
    #     return eps
    #
    # @property
    # def name(self):
    #     # if self.n:
    #     #     return self.n
    #     try:
    #         _name = self.links['/oic/con'].data['n']
    #         if _name:
    #             return _name
    #         # return self.n
    #     except KeyError:
    #         pass
    #     try:
    #         return self.links['/oic/d'].data['n']
    #         # return self.n
    #     except KeyError:
    #         return ''
    #
    # def get(self, param_path, *args):
    #     _param_path = param_path.split('.')
    #     _data = self.data
    #     for elem in _param_path:
    #         try:
    #             _data = _data[elem]
    #         except KeyError:
    #             if len(args) > 0:
    #                 return args[0]
    #             raise KeyError(param_path)
    #     return _data
    #
    # def to_object_data(self):
    #     res = []
    #     for href in self.links:
    #         data = self.links[href].data
    #         if 'rt' not in data or 'if' not in data:
    #             raise ExtException(message='bad resource', detail=f'{href} - rt or if not defined')
    #         res.append({
    #             'href': href,
    #             'rt': self.links[href].data['rt'],
    #             'if': self.links[href].data['if'],
    #             'n': self.links[href].name
    #         })
    #     return {
    #         '_id': self.di,
    #         'n': self.name,
    #         'ep': self.eps[0]['ep'] if self.eps else None,
    #         'res': res
    #     }
    async def retrieve(self, sender_device, href, data, *, secure=None, **kwargs):
        res = ResourceLink(self.data)
        res.href = href
        resp = await res.retrieve(
            sender_device,
            data,
            secure=secure,
            **kwargs
        )
        return resp

    async def update(self, sender_device, href, data, *, secure=None, **kwargs):
        res = ResourceLink(self.data)
        res.href = href
        resp = await res.update(
            sender_device,
            data,
            secure=secure,
            **kwargs
        )
        return resp

    async def device_ownership(self, sender_device: Device, owner_uuid: str, *, new_di=str(uuid4()),
                               sid=None, cis=None, apn='bubot'):
        ...
        # post coap  /oic/sec/doxm {'oxmsel': 0} метод передачи владельца Just-Works
        await self.update(sender_device, '/oic/sec/doxm', {
            'oxmsel': 0,
            'devowneruuid': owner_uuid,
            'rowneruuid': owner_uuid,
            'deviceuuid': new_di
        }, secure=True)
        # post coaps /oic/sec/pstat {'om': 4} операция подготовки выполняется клиентом
        await self.update(sender_device, '/oic/sec/pstat', {
            'om': 4,
            'rowneruuid': owner_uuid
        }, secure=True)

        # POST coaps /oic/sec/doxm {'devowneruuid': '<owner uuid>'}
        # POST coaps /oic/sec/doxm {'deviceuuid': '<new device uuid>'}
        # POST coaps /oic/sec/doxm {'rowneruuid': '<owner uuid>'}
        # POST coaps /oic/sec/acl2 {'rowneruuid': '<owner uuid>'}
        await self.update(sender_device, '/oic/sec/acl2', {
            'rowneruuid': owner_uuid
        }, secure=True)
        # POST coaps /oic/sec/pstat {'rowneruuid': '<owner uuid>'}
        # POST coaps /oic/sec/cred {'creds': [{'credtype': 1, 'subjectuuid': '<owner uuid>', 'privatedata': {'encoding': 'oic.sec.encoding.raw', 'data': b''}}], 'rowneruuid': '<owner uuid>'}
        await self.update(sender_device, '/oic/sec/cred', {
            'creds': [{
                'credtype': 1,
                'subjectuuid': owner_uuid,
                'privatedata': {'encoding': 'oic.sec.encoding.raw', 'data': ''}
            }],
            'rowneruuid': owner_uuid
        }, secure=True)
        # POST coaps /oic/sec/sdi {'uuid': '00000000-0000-0000-0000-000000000000', 'name': '', 'priv': False}
        await self.update(sender_device, '/oic/sec/sdi', {
            'uuid': '00000000-0000-0000-0000-000000000000', 'name': '', 'priv': False
        }, secure=True)
        # POST coaps /oic/sec/doxm {'owned': True}
        await self.update(sender_device, '/oic/sec/doxm', {'owned': True}, secure=True)
        # POST coaps /oic/sec/pstat {'dos': {'s': 2}}
        await self.update(sender_device, '/oic/sec/pstat', {'dos': {'s': 2}}, secure=True)
        cloud_conf = {}
        if cis and sid:
            await self.update(sender_device, '/CoAPCloudConfResURI', {
                'sid': sid,
                'cis': cis,
                'apn': apn
            }, secure=True)
