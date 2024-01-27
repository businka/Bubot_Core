import urllib.parse

from bubot_helpers.ExtException import ExtException, ExtTimeoutError
# from bubot.core.Coap.coap import Message
from bubot_helpers.Helper import ArrayHelper


# _logger = logging.getLogger(__name__)


class ResourceLink:
    def __init__(self, data=None):
        self.data = {} if data is None else data
        self.bm = 0
        self.observe = False

    def __bool__(self):
        if not self.data or not self.href or not self.get_endpoint():
            return False
        return True

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
        self.parse_uri(f'coap://{msg.remote[0]}:{msg.remote[1]}')
        self.href = '/'.join(msg.opt.uri_path)
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
            uid = f'ocf://{self.di}'
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
            self.data['anchor'] = f'ocf://{self.di}'
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
                self.data['eps'].append(dict(ep=f'{uri[0]}://{uri[1]}'))
        if uri[2]:
            self.data['href'] = uri[2]

    async def retrieve(self, sender_device, data=None, **kwargs):
        # _log.debug('retrieve {}'.format(self.href))
        resp = await sender_device.transport_layer.send_message('retrieve', self, data,
                                                                ack=True,
                                                                **kwargs)
        # _log.debug('retrieve {} {}'.format(self.href, _data.cn))
        return resp.decode_payload()

    async def update(self, sender_device, data, **kwargs):
        # _log.debug('retrieve {}'.format(self.href))
        # to = ResourceLink.init(self.data)
        resp = await sender_device.transport_layer.send_message(
            'update',
            self,
            data,
            ack=True,
            **kwargs
        )
        # _log.debug('retrieve {} {}'.format(self.href, _data.cn))
        return resp.decode_payload()

    async def check_live(self, sender_device):
        try:
            if not self.href:
                raise ExtException(message='href not defined', detail=f'{self.di}')
            return await self.retrieve(sender_device), False
        except ExtTimeoutError:
            href = self.href
            found_link = await sender_device.transport_layer.find_device(self.di)
            if found_link:
                sender_device.log.info(f'Link {self.di} {self.href} found')
                found_link['href'] = href
                return await self.retrieve(sender_device), True

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
            return f"ocf://{self.data['di']}"

    @property
    def name(self):
        if self.data.get('n'):
            return self.data['n']
        return self.data['href']

    def get_endpoint_by_scheme(self, scheme):
        for elem in self.data['eps']:
            ep: str = elem['ep']
            if ep.startswith(scheme):
                return elem

    def get_endpoint(self):
        try:
            return self.data['eps'][0]['ep']
        except IndexError:
            return ''

    def get_endpoint_address(self):
        try:
            return tuple(urllib.parse.urlparse(self.get_endpoint()).netloc.split(':'))
        except IndexError:
            return ''

    @property
    def discoverable(self):
        _bm = self.data['p'].get('bm', 0)
        if _bm > 0:
            return int(bin(_bm)[-1])
        return 0

    def __str__(self):
        result = self.get_endpoint()
        if self.href:
            result += f'{self.href}'
        return result
