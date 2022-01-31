from Bubot.OcfResource.OcfResource import OcfResource
from Bubot_CoAP.defines import Codes


class OicRPstat(OcfResource):
    async def render_GET(self, request):
        raise NotImplementedError(self.__class__.__name__)

    async def render_GET_advanced(self, request, response):
        self.debug('get', request)
        response.code = Codes.CONTENT.number
        response.content_type = self.actual_content_type
        return self, response

    async def render_POST_advanced(self, request, response):
        self.debug('post', request)
        response.code = Codes.CHANGED.number
        return self, response
