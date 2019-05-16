from bubot.devices.Device.Device import Device
from .__init__ import __version__ as device_version
import asyncio
import logging

# _logger = logging.getLogger(__name__)


class EchoDevice(Device):
    version = device_version
    file = __file__

    async def on_idle(self):
        i = self.get_param('/oic/mnt', 'i')
        self.set_param('/oic/mnt', 'i', i + 1)
        self.log.info('i: {}'.format(i))
        await asyncio.sleep(1)

    def get_install_actions(self):
        result = [
            dict(
                id='search_devices',
                icon='search',
                title='search devices'
            )
        ]
        result.extend(super().get_install_actions())
        return result

    async def on_action(self, message, answer):
        j = self.get_param('/oic/mnt', 'j')
        self.set_param('/oic/mnt', 'j', j + 1)
        self.log.info('j: {}'.format(j))
