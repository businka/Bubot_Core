from enum import Enum

from bubot.OcfResource.OcfResource import OcfResource
from bubot_helpers.ExtException import ExtException


class DosS(Enum):
    RESET = 0  # Device reset state
    RFOTM = 1  # Ready for Device owner transfer method state
    RFPRO = 2  # Ready for Device provisioning state
    RFNOP = 3  # Ready for Device normal operation state
    SRESET = 4  # The Device is in a soft reset state


class OicRPstat(OcfResource):
    ...

    async def _on_post(self, request, payload, response):
        await super()._on_post(request, payload, response)
        new_state = None
        try:
            new_state = payload['dos']['s']
        except KeyError:
            pass
        if new_state == DosS.RFPRO.value:
            self.device.loop.create_task(self.on_ready_provisioning())
        return self.payload

    async def on_ready_provisioning(self):
        try:
            current_di = self.device.get_param('/oic/d', 'di')
            owner_di = self.device.get_param('/oic/sec/doxm', 'deviceuuid')
            if current_di != owner_di and self.device.get_param('/oic/sec/doxm', 'owned'):
                self.device.update_param('/oic/d', 'di', owner_di)
                await self.device.transport_layer.restart_coaps_endpoints()
            self.device.update_param('/oic/sec/pstat', None, {
                'isop': True,
                'dos': {'s': DosS.RFNOP.value}
            })
            self.device.save_config()
        except Exception as err:
            raise ExtException(parent=err)
