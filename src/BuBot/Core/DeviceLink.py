import asyncio
import urllib.parse

# from Bubot.Core.Coap.coap import Message
from Bubot.Helpers.ExtException import ExtException
from Bubot.Helpers.Helper import ArrayHelper


# _logger = logging.getLogger(__name__)


class ResourceLink:
    def __init__(self):
        self.data = {}
        self.bm = 0
        self.observe = False

    @classmethod
    def init(cls, value):
        if isinstance(value, str):  # uri
            return cls.init_from_uri(value)
        if isinstance(value, dict):
            return cls.init_from_link(value)
        # if isinstance(value, Message):
        #     return cls.init_from_msg(value)
        if isinstance(value, ResourceLink):
            return value
        return None

    @classmethod
    def init_from_uri(cls, uri):
        self = cls()
        self.parse_uri(uri)
        return self

    @classmethod
    def init_from_msg(cls, msg):
        self = cls()
        self.parse_uri(msg.opt.uri_host)
        self.parse_uri('coap://{0}:{1}'.format(msg.remote[0], msg.remote[1]))
        self.href = '/{}'.format('/'.join(msg.opt.uri_path))
        return self

    @classmethod
    def init_from_link(cls, link, **kwargs):
        self = cls()
        self._parse_link(link)
        return self

    def set_data(self, _name, src, *args):
        try:
            self.data[_name] = src[_name]
        except KeyError:
            try:
                self.data[_name] = args[0]
            except IndexError:
                pass

    @property
    def uid(self):
        if self.di:
            uid = 'ocf://{}'.format(self.di)
        else:
            uid = self.get_endpoint()

        href = self.href
        if href:
            uid += href
        return uid

    @classmethod
    def init_from_device(cls, device, href, **kwargs):
        new_data = device.data[href]
        self = cls()
        self.di = device.di
        self.data['anchor'] = 'ocf://{}'.format(self.di)
        self.data['eps'] = device.eps
        self.data['href'] = href
        self.set_data('id', new_data)
        self.set_data('rt', new_data)
        self.set_data('if', new_data)
        self.set_data('n', new_data)
        self.set_data('p', new_data, dict(bm=0))
        return self

    def get(self, name, default=None):
        return self.data.get(name, default)

    @staticmethod
    def get_default_data():
        return {
            # 'di': '',  # device id
            'href': '',  # resource
            'anchor': '',  # ocf uri
            'title': '',  # ocf uri
            'id': '',  # id resource
            'n': '',  # name resource
            'rt': [],
            'if': [],
            'eps': [],
            'p': {}
        }

    def _parse_link(self, link):
        self.data = self.get_default_data()
        self.set_data('di', link)
        if self.di:
            self.data['anchor'] = 'ocf://{}'.format(self.di)
        else:
            self.parse_uri(link.get('anchor'))
        self.parse_uri(link.get('href'))
        self.set_data('id', link)
        self.set_data('rt', link)
        self.set_data('if', link)
        self.set_data('n', link)
        self.set_data('p', link, dict(bm=0))
        if 'eps' in link:
            for ep in link['eps']:
                ArrayHelper.update(self.data['eps'], ep, 'ep')
        if 'ep' in link:
            ArrayHelper.update(self.data['eps'], dict(ep=link['ep']), 'ep')

    def parse_uri(self, _uri):
        if _uri is None:
            return
        uri = urllib.parse.urlparse(_uri)  # (scheme, netloc, path, params, query, fragment)
        if uri[0]:
            if uri[0] == 'ocf':
                self.data['di'] = uri[1]
            elif uri[0] == 'coap' or uri[0] == 'coaps':
                if 'eps' not in self.data:
                    self.data['eps'] = []
                self.data['eps'].append(dict(ep='{0}://{1}'.format(uri[0], uri[1])))
        if uri[2]:
            self.data['href'] = uri[2]

    async def retrieve(self, sender_device):
        # _log.debug('retrieve {}'.format(self.href))
        _data = await sender_device.request(
            'retrieve',
            self.data,
            None
        )
        # _log.debug('retrieve {} {}'.format(self.href, _data.cn))
        return _data.cn

    @property
    def di(self):
        return self.data.get('di')

    @di.setter
    def di(self, value):
        self.data['di'] = value

    @property
    def href(self):
        return self.data.get('href')

    @href.setter
    def href(self, value):
        self.data['href'] = value

    @property
    def anchor(self):
        if self.data.get('anchor'):
            return self.data['anchor']
        if self.data.get('di'):
            return 'ocf://{}'.format(self.data['di'])

    @property
    def name(self):
        if self.data.get('n'):
            return self.data['n']
        return self.data['href']

    def get_endpoint(self):
        try:
            return self.data['eps'][0]['ep']
        except IndexError:
            return ''

    @property
    def discoverable(self):
        _bm = self.data['p'].get('bm', 0)
        if _bm > 0:
            return int(bin(_bm)[-1])
        return 0


class DeviceLink:
    def __init__(self):
        self.links = {}
        self.data = {}
        self.di = None
        # self.n = None
        self.eps = None

    @classmethod
    def get_default_link(cls):
        return {
            'di': '',  # device id
            'href': '',  # resource
            'anchor': '',  # ocf uri
            'rt': [],
            'if': [],
            'eps': [],
            'p': {}
        }

    @classmethod
    def get_resource_by_uri(cls, resources, uri):
        link = ResourceLink.init_from_uri(uri)
        if not link.di:
            raise ExtException(message='bad schema id, need ocf')
        try:
            return resources[link.di].links[link.href]
        except KeyError:
            raise ExtException(message='resource not found', detail=uri)

    @classmethod
    def init_from_oic_res(cls, data):
        self = cls()
        self.di = data['di']
        # self.n = data.get('n', '')
        for link in data['links']:
            data = ResourceLink.init_from_link(link, di=self.di)
            self.links[data.get('href')] = data
            self.eps = data.data['eps']
        return self

    @classmethod
    def init_from_doxm_msg(cls, msg):
        self = cls()
        data = msg.decode_payload()
        self.di = data['deviceuuid']
        for link in data['links']:
            data = ResourceLink.init_from_link(data, di=self.di)
            self.links[data.get('href')] = data
            self.eps = data.data['eps']
        return self

    def update_from_oic_res(self, data):
        raise NotImplementedError()

    async def retrieve(self, sender_device, link):
        _data = self.links[link].retrieve(sender_device)
        return _data

    async def retrieve_all(self, sender_device):
        requests = []
        index = []
        result = []
        for href in self.links:
            if href == '/oic/res':
                continue
            index.append(href)
            requests.append(self.links[href].retrieve(sender_device))
        result = await asyncio.gather(*requests, return_exceptions=True, loop=sender_device.loop)
        for i in range(len(result)):
            if not isinstance(result[i], Exception):
                self.data[index[i]] = result[i]
        pass

    @classmethod
    def init_from_device(cls, device):
        self = cls()
        self.data = device.data
        self.di = device.get_device_id()
        self.eps = self.get_device_eps(device)
        for res in self.data:
            self.links[res] = ResourceLink.init_from_device(self, res)
        return self

    @staticmethod
    def get_device_eps(device):
        eps = []
        if device.coap and device.coap.endpoint:
            for elem in device.coap.endpoint:
                if elem == 'multicast' or not device.coap.endpoint[elem]:
                    continue
                eps.append(dict(ep=device.coap.endpoint[elem]['uri']))
        return eps

    @property
    def name(self):
        # if self.n:
        #     return self.n
        try:
            _name = self.links['/oic/con'].data['n']
            if _name:
                return _name
            # return self.n
        except KeyError:
            pass
        try:
            return self.links['/oic/d'].data['n']
            # return self.n
        except KeyError:
            return ''

    def get(self, param_path, *args):
        _param_path = param_path.split('.')
        _data = self.data
        for elem in _param_path:
            try:
                _data = _data[elem]
            except KeyError:
                if len(args) > 0:
                    return args[0]
                raise KeyError(param_path)
        return _data

    def to_object_data(self):
        res = []
        for href in self.links:
            data = self.links[href].data
            if 'rt' not in data or 'if' not in data:
                raise ExtException(message='bad resource', detail=f'{href} - rt or if not defined')
            res.append({
                'href': href,
                'rt': self.links[href].data['rt'],
                'if': self.links[href].data['if'],
                'n': self.links[href].name
            })
        return {
            '_id': self.di,
            'n': self.name,
            'ep': self.eps[0]['ep'] if self.eps else None,
            'res': res
        }
