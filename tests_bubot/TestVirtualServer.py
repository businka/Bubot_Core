import unittest
import logging
import asyncio
from BubotObj.OcfDevice.subtype.VirtualServer.VirtualServer import VirtualServer as Device
from Bubot.Core.OcfMessage import OcfRequest
from Bubot.Core.DeviceLink import ResourceLink
from Bubot.Core.TestHelper import async_test, wait_run_device, get_config_path, wait_run_device2
from os import path


class TestVirtualServer(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.DEBUG)
        self.config_path = '{}/config/'.format(path.dirname(__file__))

    @async_test
    async def test_add_delete_device_from_update_running_device(self):
        await self.add_delete_device_from_update_running_device(Device)

    async def add_delete_device_from_update_running_device(self, virtual_server_class):
        device = virtual_server_class.init_from_config()
        device_task = asyncio.create_task(device.main())
        while device.get_param('/oic/mnt', 'status') == 'init':
            try:
                device_task.result()
            except asyncio.InvalidStateError:
                pass
            await asyncio.sleep(0.1)
        msg = OcfRequest(cn={
            "running_devices": [
                {
                    "dmno": "EchoDevice",
                    "n": "Test1"
                },
                {
                    "dmno": "EchoDevice",
                    "n": "Test2"
                }
            ]
        })
        await device.post_devices(msg)
        await asyncio.sleep(0.2)
        devices = device.get_param(*device.run_dev)
        self.assertEqual(len(devices), 2, 'count devices')

        # удаляем девайс
        msg = OcfRequest(cn={
            "running_devices": [devices[0]]
        })
        await device.post_devices(msg)
        await asyncio.sleep(0.1)
        devices = device.get_param(*device.run_dev)
        self.assertEqual(len(devices), 1, 'count devices')
        device_task.cancel()
        try:
            await device_task
        except asyncio.CancelledError:
            pass

    @async_test
    async def test_find_drivers(self):
        res = Device.init_from_config().find_drivers()
        this_found = False
        root_found = False
        for elem in res:
            if elem == Device.__name__:
                this_found = True
            elif elem == 'Device':
                root_found = True
        self.assertTrue(this_found)
        self.assertTrue(root_found)

    @async_test
    async def test_run_several_virtual_server(self):
        device = Device.init_from_file('VirtualServer', '3')
        device.run()
        device_task = await wait_run_device2(device)
        # device1_task = await wait_run_device(device._running_devices['4'][0])

        while True:
            res = await device.find_resource_by_link(ResourceLink.init_from_link(dict(di='2', href='/oic/mnt')))
            if res:
                break
        await device.cancel()
        await asyncio.wait_for(device_task, 30)

        pass


if __name__ == '__main__':
    unittest.main()
