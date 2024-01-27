from Bubot.OcfResource.OcfResource import OcfResource
from Bubot.OcfResource.OicRAcl2 import OicRAcl2
from Bubot.OcfResource.OicRCred import OicRCred
from Bubot.OcfResource.OicRDoxm import OicRDoxm
from Bubot.OcfResource.OicRPstat import OicRPstat
from Bubot.OcfResource.OicRSdi import OicRSdi
from Bubot.OcfResource.OicWkRes import OicWkRes


class ResourceLayer:
    def __init__(self, device):
        self.device = device
        self._handlers = {
            '/oic/res': OicWkRes,
            '/oic/sec/doxm': OicRDoxm,
            '/oic/sec/pstat': OicRPstat,
            '/oic/sec/cred': OicRCred,
            '/oic/sec/acl2': OicRAcl2,
            '/oic/sec/sdi': OicRSdi
        }
        pass

    def add_handler(self, href, handler):
        self._handlers[href] = handler

    def init_from_config(self, config):
        self.device.res = {}
        for href in config:
            _handler = self._handlers.get(href, OcfResource).init_from_config(self.device, href, config[href])
            self.device.res[href] = _handler
