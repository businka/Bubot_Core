from Bubot.OcfResource.OcfResource import OcfResource
from Bubot.OcfResource.OicWkRes import OicWkRes
from Bubot.OcfResource.OicRDoxm import OicRDoxm


class ResourceLayer:
    def __init__(self, device):
        self.device = device
        self._handlers = {
            '/oic/res': OicWkRes,
            '/oic/sec/doxm': OicRDoxm
        }
        pass

    def add_handler(self, href, handler):
        self._handlers[href] = handler

    def init_from_config(self, config):
        self.device.res = {}
        for href in config:
            _handler = self._handlers.get(href, OcfResource).init_from_config(self.device, href, config[href])
            self.device.res[href] = _handler
