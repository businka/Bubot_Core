from Bubot_CoAP import defines
from Bubot_CoAP.defines import Codes
from Bubot_CoAP.messages.option import Option
from bubot.OcfResource.OcfResource import OcfResource


class OicRDoxm(OcfResource):

    async def render_GET(self, request, response):
        query = request.query

        owned = query.get('owned')
        if owned:
            is_owned = True if owned[0].upper() == 'TRUE' else False
            if self.data['owned'] != is_owned:
                return self, None

        di = query.get('di')
        if di:
            if self.device.di not in di:
                return self, None

        try:
            ep = self.device.transport_layer.coap.endpoint_layer.find_sending_endpoint(request)
            if ep and request.source == ep.address:  # сами себя не находим
                return self, None
        except KeyError:
            pass

        response.add_option(Option(defines.OptionRegistry.CONTENT_TYPE, 10000))
        response.code = Codes.CONTENT.number
        response.encode_payload(self.payload)
        response.acknowledged = True

        self.device.log.debug(
            f'{self.__class__.__name__} get {self._href} {request.query} {request.decode_payload()} '
            f'from {request.source} {request.destination}')
        return self, response

    def set_state_soft_reset(self):
        self.device.update_param('/oic/sec/doxm', None, {
            'owned': False,
            'devowneruuid': "00000000-0000-0000-0000-000000000000",
            'rowneruuid': "00000000-0000-0000-0000-000000000000"
            # 'deviceuuid': ''
        })
        self.device.update_param('/oic/sec/pstat', None, {
            'isop': False,
            'dos': {
                'p': True,
                's': 0
            },
            'om': 0,
            'sm': 0,
            'rowneruuid': "00000000-0000-0000-0000-000000000000"
        })
        self.device.update_param('/oic/sec/ael', None, {
            'usedspace': 0,
            'categoryfilter': None,
            'priorityfilter': None,
            'events': [],

        })
        self.device.update_param('/oic/sec/sp', None, {
            'supportedprofiles': None,
            'currentprofile': None
        })
        self.device.update_param('/oic/sec/sdi', None, {
            'uuid': "00000000-0000-0000-0000-000000000000",
            'name': '',
            'priv': False
        })
        self.device.update_param('/oic/sec/acl2', None, {
            'rowneruuid': "00000000-0000-0000-0000-000000000000"
        })
        self.device.update_param('/oic/sec/cred', None, {
            'rowneruuid': "00000000-0000-0000-0000-000000000000"
        })

    def set_state_ready_for_otm(self):
        if self.device.get_param('/oic/sec/doxm', 'owned') \
                or self.device.get_param('/oic/sec/doxm', 'devowneruuid') == "00000000-0000-0000-0000-000000000000":
            raise NotImplementedError()
        cred = self.device.get_param('/oic/sec/cred')
        self.device.update_param('/oic/sec/doxm', None, {
            'owned': True,
        })

    def check_state_ready_for_provisioning(self):
        devowneruuid = self.device.get_param('/oic/sec/doxm', 'devowneruuid')
        rowneruuid = self.device.get_param('/oic/sec/doxm', 'rowneruuid')
        if self.device.get_param('/oic/sec/doxm', 'owned') \
                and devowneruuid != "00000000-0000-0000-0000-000000000000" \
                and rowneruuid != "00000000-0000-0000-0000-000000000000" \
                and self.device.get_param('/oic/sec/doxm', 'deviceuuid') != "00000000-0000-0000-0000-000000000000" \
                and self.device.get_param('/oic/sec/pstat', 'isop') == False \
                and self.device.get_param('/oic/sec/pstat', 'dos')['s'] == 2:
            raise NotImplementedError()
        cred = self.device.get_param('/oic/sec/cred')
        # todo devowner and rowner in cred
        self.device.update_param('/oic/sec/doxm', None, {
            'owned': True,
        })

    def check_state_ready_for_normal_operation(self):
        devowneruuid = self.device.get_param('/oic/sec/doxm', 'devowneruuid')
        rowneruuid = self.device.get_param('/oic/sec/doxm', 'rowneruuid')
        device_uuid = self.device.get_param('/oic/sec/doxm', 'deviceuuid')
        if self.device.get_param('/oic/sec/doxm', 'owned') \
                and devowneruuid != "00000000-0000-0000-0000-000000000000" \
                and rowneruuid != "00000000-0000-0000-0000-000000000000" \
                and self.device.get_param('/oic/sec/doxm', 'deviceuuid') != "00000000-0000-0000-0000-000000000000" \
                and device_uuid == self.device.get_param('/oic/d', 'di') \
                and self.device.get_param('/oic/sec/pstat', 'dos')['s'] == 3:
            raise NotImplementedError()
        cred = self.device.get_param('/oic/sec/cred')
        # todo devowner and rowner in cred
        self.device.update_param('/oic/sec/doxm', None, {
            'owned': True,
        })
