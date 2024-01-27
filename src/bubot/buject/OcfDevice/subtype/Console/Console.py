import asyncio
from datetime import datetime

from BubotObj.OcfDevice.subtype.Device.Device import Device
from .__init__ import __version__ as device_version


# _logger = logging.getLogger(__name__)


class Console(Device):
    version = device_version
    file = __file__
    template = False

    async def on_idle(self):
        i = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        self.set_param('/oic/mnt', 'DateTime', i)
        self.log.info('DateTime: {}'.format(i))
        await asyncio.sleep(1)

    def get_install_actions(self):
        result = [
            dict(
                id='search_devices',
                icon='mdi-radar',
                title='search OcfDriver'
            )
        ]
        result.extend(super().get_install_actions())
        return result

    async def on_action(self, message, answer):
        j = self.get_param('/oic/mnt', 'j')
        self.set_param('/oic/mnt', 'j', j + 1)
        self.log.info('j: {}'.format(j))

    async def on_update_console(self, message, answer):
        self.log.debug('{0} receive notify {1} {2}'.format(
            self.__class__.__name__, message.to.di, message.to.href))
        self.log.info(str(message))
