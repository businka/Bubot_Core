from bubot.OcfResource.OcfResource import OcfResource


class ResourceLayer:
    def __init__(self, device):
        self.device = device
        if not hasattr(self, '_handlers'):
            self._handlers = {}
        pass

    def add_handler(self, href, handler):
        self._handlers[href] = handler

    def init_from_config(self, config):
        self.device.res = {}
        for href in config:
            _handler = self._handlers.get(href, OcfResource).init_from_config(self.device, href, config[href])
            self.device.res[href] = _handler
        for href in self._handlers:
            if href not in self.device.res:
                _handler = self._handlers.get(href, OcfResource).init_from_config(self.device, href, {})
                self.device.res[href] = _handler
