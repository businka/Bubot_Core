from Bubot.Helpers.ExtException import KeyNotFound
from Bubot_CoAP.resources.resource import Resource


class OcfResource(Resource):
    def __init__(self, name, coap_server=None, visible=True, observable=True, allow_children=True):
        super().__init__(name, coap_server=None, visible=True, observable=True, allow_children=True)
        self._data = {}
        self._href = name
        self.actual_content_type = "application/vnd.ocf+cbor"
        self.content_type = "application/vnd.ocf+cbor"
        self.device = None
        pass

    @classmethod
    def init_from_config(cls, device, href, config):
        self = cls(href)
        self.device = device
        self.data = config
        return self

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    @property
    def payload(self):
        return self._data

    # @payload.setter
    # def payload(self, value):
    #     self._data = value

    def get_attr(self, *args):
        try:
            return self.data[args[0]]
        except KeyError:
            try:
                return args[1]
            except IndexError:
                raise KeyNotFound(
                    action='OcfDevice.get_param',
                    detail=f'{args[0]} ({self.__class__.__name__}{self._href})'
                ) from None

    def set_attr(self, name, value):
        self.data[name] = value

    @property
    def resource_type(self):
        return self._data.get('rt', [])

    @property
    def interface_type(self):
        return self._data.get('if', [])

    def get_link(self, request_address):
        return {
            'anchor': f'ocf://{self.device.get_device_id()}',
            'href': self._href,
            'eps': self.device.transport_layer.get_eps(request_address[0] if request_address else None),
            'rt': self.get_attr('rt', []),
            'if': self.get_attr('if', []),
            'n': self.get_attr('n', ''),
            'p': self.get_attr('p', dict(bm=0)),
        }

    async def render_GET(self, request):
        self.device.log.debug(
            f'{self.__class__.__name__} get {self._href} {request.query} from {request.source} to {request.destination} ')
        return self

    def debug(self, method, request):
        self.device.log.debug(
            f'{self.__class__.__name__} {method} {self._href} {request.query} {request.decode_payload()} from {request.source} {request.destination}')
