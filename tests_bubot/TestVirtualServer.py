import asyncio
import logging
import unittest
from os import path

from Bubot.Core.DeviceLink import ResourceLink
from Bubot.Core.TestHelper import async_test, wait_run_device
from Bubot.Ocf.OcfMessage import OcfRequest
from BubotObj.OcfDevice.subtype.VirtualServer.VirtualServer import VirtualServer as Device


class TestVirtualServer(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.DEBUG)
        self.config_path = path.dirname(__file__)

    @async_test
    async def test_add_delete_device_from_update_running_device(self):
        await self.add_delete_device_from_update_running_device(Device)

    async def add_delete_device_from_update_running_device(self, virtual_server_class):
        device = virtual_server_class.init_from_config()
        device_task = await wait_run_device(device)

        msg = OcfRequest(
            to={'href': '/oic/con'},
            op='update',
            cn={"running_devices": [
                {
                    "dmno": "EchoDevice",
                    "n": "Test1",
                    "di": "10000000-0000-0000-0000-000000000001"
                },
                {
                    "dmno": "EchoDevice",
                    "n": "Test2",
                    "di": "10000000-0000-0000-0000-000000000002"
                }
            ]
            })
        await device.on_post_request(msg)
        await asyncio.sleep(0.2)
        devices = device.get_param(*device.run_dev)
        self.assertEqual(len(devices), 2, 'count devices')

        # удаляем девайс
        msg = OcfRequest(
            to={'href': '/oic/con'},
            op='update',
            cn={
                "running_devices": [devices[0]]
            })
        await device.on_post_request(msg)
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
        device = Device.init_from_file(
            class_name='VirtualServer',
            di='30000000-0000-0000-0000-000000000003',
            path=self.config_path)
        device_task = await wait_run_device(device)
        # device1_task = await wait_run_device(device._running_devices['4'][0])

        while True:
            res = await device.transport_layer.find_resource_by_link(ResourceLink.init_from_link(
                dict(di='30000000-0000-0000-0000-000000000004', href='/oic/mnt')))
            if res:
                break
        await device.cancel()
        await asyncio.wait_for(device_task, 30)

        pass


if __name__ == '__main__':
    unittest.main()
