import unittest
import logging
import asyncio
from bubot.buject.OcfDevice.subtype.Device.Device import Device
from bubot.core.ResourceLink import DeviceLink, ResourceLink
from bubot.core.TestHelper import async_test, wait_run_device, get_config_path
from os import path


class TestDeviceLinkSimple(unittest.TestCase):
    @async_test
    async def test_init_from_oic_res(self):
        data = dict(di='1', links=[
            {'anchor': 'ocf://1', 'href': '/oic/p', 'rt': ['oic.wk.p'], 'if': ['oic.if.baseline'], 'p': {'bm': 1},
             'eps': [{'ep': 'coap://[2a00:84c0:300:19b0:cc1c:9ee0:4f96:7557]:11111'}]},
            {'anchor': 'ocf://1', 'href': '/oic/d', 'rt': ['oic.wk.d'], 'if': ['oic.if.baseline'], 'p': {'bm': 1},
             'eps': [{'ep': 'coap://[2a00:84c0:300:19b0:cc1c:9ee0:4f96:7557]:11111'}]},
            {'anchor': 'ocf://1', 'href': '/oic/con', 'rt': ['oic.wk.con', 'bubot.con'], 'if': ['oic.if.baseline'],
             'p': {'bm': 3}, 'eps': [{'ep': 'coap://[2a00:84c0:300:19b0:cc1c:9ee0:4f96:7557]:11111'}]}])
        link = DeviceLink.init_from_oic_res(data)

        pass


class TestDeviceLink(unittest.TestCase):

    @async_test
    async def setUp(self):
        logging.basicConfig(level=logging.DEBUG)
        self.config_path = '{}/config/'.format(path.dirname(__file__))
        self.device = Device.init_from_file(di='1', class_name='EchoDevice', path=self.config_path)
        self.device_task = asyncio.create_task(self.device.main())
        while self.device.get_param('/oic/mnt', 'status') == 'init':
            try:
                self.device_task.result()
            except asyncio.InvalidStateError:
                pass
            await asyncio.sleep(0.1)
        self.assertEqual(self.device.get_param('/oic/mnt', 'status'), 'run', 'status bubot device')

    @async_test
    async def tearDown(self):
        self.device_task.cancel()
        await self.device_task
        self.assertTrue(self.device.coap.endpoint['IPv6']['transport'].is_closing(), 'clossing coap')
        self.assertTrue(self.device.coap.endpoint['multicast'][0]['transport'].is_closing(), 'run IPv6 transport')

    @async_test
    async def test_discovery_device(self):
        result = await self.device.discovery_resource()
        self.assertIn(self.device.get_device_id(), result)

    @async_test
    async def test_retrieve_device(self):
        di = self.device.get_device_id()
        result = await self.device.discovery_resource()
        self.assertIn(di, result)

        link = DeviceLink.init_from_oic_res(dict(di=di, links=result[di]))
        res = await link.retrieve(self.device)

        pass




if __name__ == '__main__':
    unittest.main()
