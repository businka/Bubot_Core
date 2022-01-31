import asyncio

from BubotObj.OcfDevice.subtype.Device.Device import Device
from .__init__ import __version__ as device_version


# _logger = logging.getLogger(__name__)


class EchoDevice(Device):
    version = device_version
    template = False
    file = __file__

    async def on_idle(self):
        i = self.get_param('/oic/mnt', 'i')
        self.set_param('/oic/mnt', 'i', i + 1)
        self.log.info('i: {}'.format(i))
        await asyncio.sleep(1)

    @classmethod
    def get_install_actions(cls):
        result = [
            cls.get_install_search_action()
        ]
        result.extend(super().get_install_actions())
        return result

    async def on_action(self, message, answer):
        j = self.get_param('/oic/mnt', 'j')
        self.set_param('/oic/mnt', 'j', j + 1)
        self.log.info('j: {}'.format(j))

    async def find_devices(self, **kwargs):
        notify = kwargs.get('notify')
        if notify:
            await notify({'message': f'Ищем {self.__class__.__name__}...'})
        result = []
        for i in range(2):
            await asyncio.sleep(1)
            if notify:
                await notify({'message': f'Найдено {self.__class__.__name__}: {i + 1}'})
            tmp_device = EchoDevice.init_from_config({})
            result.append(dict(
                id=tmp_device.get_device_id(),
                name=tmp_device.get_device_name(),
                links=tmp_device.get_discover_res(),
                _actions=Device.get_install_actions()
            ))
        return result
