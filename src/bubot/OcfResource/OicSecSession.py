from bubot.OcfResource.OcfResource import OcfResource


class OicSecSession(OcfResource):
    def __init__(self, name, coap_server=None, visible=True, observable=True, allow_children=True):
        super().__init__(name, coap_server=None, visible=False, observable=False, allow_children=True)

        ...
