from Bubot.OcfResource.OcfResource import OcfResource
from Bubot_CoAP.defines import Codes


class OicRDoxm(OcfResource):
    async def render_GET(self, request):
        raise NotImplementedError(self.__class__.__name__)

    async def render_GET_advanced(self, request, response):
        query = request.query
        try:
            is_owned = True if query.get('owned', ['FALSE'])[0].upper() == 'TRUE' else False
        except:
            is_owned = False

        # if not is_owned:
        #     return self, None
        self.device.log.debug(
            f'{self.__class__.__name__} get {self._href} {request.query} {request.decode_payload()}from {request.source} {request.destination}')

        response.code = Codes.CONTENT.number
        response.content_type = self.actual_content_type
        response.encode_payload(self.payload)
        return self, response

    async def render_POST_advanced(self, request, response):
        response.code = Codes.CHANGED.number
        self.debug('post', request)
        return self, response
