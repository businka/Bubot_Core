from Bubot.Helpers.ExtException import KeyNotFound
from Bubot.OcfResource.OcfResource import OcfResource
from Bubot_CoAP.defines import Codes


class OicWkRes(OcfResource):

    @property
    def payload(self):
        return self._data

    async def render_GET(self, request):
        raise NotImplementedError(self.__class__.__name__)

    async def render_GET_advanced(self, request, response):
        query = request.query
        links = []
        for href in self.device.res:
            _res = self.device.res[href]
            if _res.visible:
                suited = True
                if query:
                    for key in query:
                        if not suited:
                            break
                        try:
                            value = self.device.res[href].get_attr(key)
                            if isinstance(value, list):
                                for elem in query[key]:
                                    if elem not in value:
                                        suited = False
                                        break
                            elif value not in query[key]:
                                suited = False
                        except KeyNotFound:
                            suited = False
                        except KeyError:
                            suited = False
                        except AttributeError:
                            suited = False
                if suited:
                    links.append(self.device.res[href].get_link(request.destination))
        self.device.log.debug(
            f'discovery {len(links)} links, get {self._href} {request.query} from {request.source} {request.destination}')
        if links:
            response.code = Codes.CONTENT.number
            response.content_type = self.actual_content_type
            response.encode_payload(links)
            return self, response

    # def get_link(self):
    #     _link = self.device.res[href].get_link()
    #     _link['anchor'] = f"{_link['anchor']}{_link['href']}"
    #     _link['ref'] = 'self'
    #     pass
