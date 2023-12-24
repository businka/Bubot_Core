from Bubot_CoAP import defines
from Bubot_CoAP.defines import Codes
from Bubot_CoAP.messages.option import Option
from Bubot_CoAP.resources.resource import Resource
from bubot_helpers.ExtException import ExtException
from bubot_helpers.ExtException import KeyNotFound


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
        data = self._data.copy()
        data.pop('rt', None)
        data.pop('if', None)
        return data

    # @payload.setter
    # def payload(self, value):
    #     self._data = value

    def get_attr(self, *args):
        try:
            return self._data[args[0]]
        except KeyError:
            try:
                return args[1]
            except IndexError:
                raise KeyNotFound(
                    action='OcfDevice.get_param',
                    detail=f'{args[0]} ({self.__class__.__name__}{self._href})'
                ) from None

    def set_attr(self, name, value):
        self._data[name] = value

    @property
    def resource_type(self):
        return self._data.get('rt', [])

    @property
    def interface_type(self):
        return self._data.get('if', [])

    def get_link(self, request_address=None):
        return {
            'anchor': f'ocf://{self.device.di}',
            'href': self._href,
            'eps': self.device.transport_layer.get_eps(request_address[0] if request_address else None),
            'rt': self.get_attr('rt', []),
            'if': self.get_attr('if', []),
            'n': self.get_attr('n', ''),
            'p': self.get_attr('p', dict(bm=0)),
        }

    async def render_GET(self, request, response):
        self.device.log.debug(
            f'{self.__class__.__name__} GET {request.scheme} {self._href} {request.query} from {request.source} to {request.destination} ')
        try:
            response.acknowledged = request.acknowledged
            await self.on_get(request)
            response.add_option(Option(defines.OptionRegistry.CONTENT_TYPE, 10000))
            response.code = Codes.CONTENT.number
            response.encode_payload(self.payload)
            return self, response
        except Exception as err:
            self.prepare_exception(response, ExtException(parent=err))
            return self, response

    async def on_get(self, request):
        return request

    def debug(self, method, request):
        self.device.log.debug(
            f'{self.__class__.__name__} {method} {self._href} {request.query} {request.decode_payload()} from {request.source} {request.destination}')

    async def render_POST(self, request, response):
        self.device.log.debug(
            f'{self.__class__.__name__} POST {request.scheme} {self._href} {request.query} from {request.source} to {request.destination} ')
        try:
            response.acknowledged = request.acknowledged
            request, response = await self.on_post(request, response)
            return request, response
        except Exception as err:
            self.prepare_exception(response, ExtException(parent=err))
            return self, response

    async def _on_post(self, request, payload, response):
        path = '/' + request.uri_path
        res = self.device.get_param(path)
        for elem in payload:
            if elem in res:
                self.device.set_param(path, elem, payload[elem])
        return self.payload

    async def on_post(self, request, response):
        request_payload = request.decode_payload()
        self.device.log.debug(request_payload)
        response_payload = await self._on_post(request, request_payload, response)
        response.code = Codes.CONTENT.number
        response.content_type = self.actual_content_type
        response.encode_payload(response_payload)
        return self, response

    @staticmethod
    def prepare_exception(response, err: ExtException):
        response.code = Codes.INTERNAL_SERVER_ERROR.number
        response.add_option(Option(defines.OptionRegistry.CONTENT_TYPE, 10000))
        response.encode_payload(err.to_dict())

    @staticmethod
    def encode_json_response(response, data):
        response.code = Codes.CONTENT.number
        response.add_option(Option(defines.OptionRegistry.CONTENT_TYPE, 10000))
        response.encode_payload(data)
