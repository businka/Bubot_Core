import unittest
import logging
import asyncio
from Bubot.Core.Coap.CoapServer import CoapServer
from BubotObj.OcfDevice.subtype.Device.Device import Device
from Bubot.Core.DeviceLink import ResourceLink
from BubotObj.OcfDevice.subtype.EchoDevice.EchoDevice import EchoDevice as EchoDevice
from Bubot.Core.TestHelper import async_test, wait_run_device
from os import path


class TestDevice(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.DEBUG)
        self.config_path = '{}/config/'.format(path.dirname(__file__))
        # self.device = Device.init_from_config()

    @async_test
    async def test_init(self):
        device = Device.init_from_file(
            di='1',
            class_name='EchoDevice',
            path=self.config_path
        )
        self.assertTrue(isinstance(device, EchoDevice), 'instance')
        self.assertEqual(device.get_param('/oic/p', 'mnpv'), Device.version, 'platform version ')
        self.assertEqual(device.get_param('/oic/d', 'sv'), device.version, 'device version')
        self.assertEqual(device.get_param('/oic/d', 'dmno'), EchoDevice.__name__, 'device class')
        self.assertEqual(device.get_param('/oic/d', 'di'), '1', 'di')
        self.assertEqual(device.get_param('/oic/con', 'udpCoapPort'), 11111, 'coap port from file')

        device = EchoDevice.init_from_file(
            di='1',
            path='{}/config/'.format(path.dirname(__file__))
        )
        self.assertTrue(isinstance(device, EchoDevice), 'instance')
        self.assertEqual(device.get_param('/oic/p', 'mnpv'), Device.version, 'platform version ')
        self.assertEqual(device.get_param('/oic/d', 'sv'), device.version, 'device version')
        self.assertEqual(device.get_param('/oic/d', 'dmno'), EchoDevice.__name__, 'device class')
        self.assertEqual(device.get_param('/oic/d', 'di'), '1', 'di')
        self.assertEqual(device.get_param('/oic/con', 'udpCoapPort'), 11111, 'coap port from file')

        pass

    @async_test
    async def test_save_config(self):
        data = b'X\x01\xb4\x85\xa0\x02\xacA\x8d\x04N*\xb3oic\x03sec\x04doxmKowned=FALSE"\'\x10\xe2\x06\xe3\x08\x00'
        ('192.168.1.15', 61689)
        device = Device.init_from_file(
            di='1',
            class_name='EchoDevice',
            path=self.config_path
        )
        device.set_device_id('3')
        data = device.save_config()
        self.assertDictEqual(data[1], {'/oic/d': {'di': '3'}, '/oic/con': {'udpCoapPort': 11111}})
        pass

    @async_test
    async def test_discover_unowned_devices(self):
        target_address = ('192.168.1.15', 50497)
        device = Device.init_from_file(
            di='00000000-0000-0000-0000-000000000001',
            class_name='EchoDevice',
            path=self.config_path
        )
        device_task = await wait_run_device(device)
        # to = ResourceLink.init_from_uri('coap://192.168.1.18:50408/oic/sec/doxm')
        # result = await device.request('retrieve', to, {}, query={'owned': ['FALSE']})
        await asyncio.sleep(10000)
        pass
        # di = device.get_device_id()
        # self.assertIn(di, result, 'device found')
        # device_task.cancel()
        # await device_task
        # self.assertTrue(device.coap.endpoint['IPv6']['transport'].is_closing(), 'clossing coap')
        # self.assertTrue(device.coap.endpoint['multicast'][0]['transport'].is_closing(), 'run IPv6 transport')
        pass

    @async_test
    async def test_discover_proxy(self):
        device = Device.init_from_file(
            di='00000000-0000-0000-0000-000000000001',
            class_name='EchoDevice',
            path=self.config_path
        )
        _remote = ('192.168.1.18', 57040)
        device_task = await wait_run_device(device)
        to = ResourceLink.init_from_uri(f'coap://{_remote[0]}:{_remote[1]}/oic/sec/doxm')
        result1 = await device.request('retrieve', to, {}, query={'owned': ['FALSE']})
        to = ResourceLink.init_from_uri(f'coap://{_remote[0]}:{_remote[1]}/oic/res')
        # result2 = await device.request('retrieve', to, {}, query={'rt': ['oic.r.doxm']})
        result2 = await device.request('retrieve', to, {})
        # _result2 = [{
        #     'anchor': 'ocf://9c048f2a-cd37-4591-53f9-e700d3b04682',
        #     'href': '/oic/sec/doxm',
        #     'rt': ['oic.r.doxm'],
        #     'if': ['oic.if.rw', 'oic.if.baseline'],
        #     'p': {'bm': 1},
        #     'eps': [{'ep': 'coap://192.168.1.18:58742', 'lat': 240}, {'ep': 'coaps://192.168.1.18:58743', 'lat': 240},
        #             {'ep': 'coap+tcp://192.168.1.18:50941', 'lat': 240},
        #             {'ep': 'coaps+tcp://192.168.1.18:50942', 'lat': 240}]}]
        print(result2)
        pass
        # await asyncio.sleep(10000)
        pass
        # di = device.get_device_id()
        # self.assertIn(di, result, 'device found')
        # device_task.cancel()
        # await device_task
        # self.assertTrue(device.coap.endpoint['IPv6']['transport'].is_closing(), 'clossing coap')
        # self.assertTrue(device.coap.endpoint['multicast'][0]['transport'].is_closing(), 'run IPv6 transport')
        pass

    @async_test
    async def test_observe_device(self):
        device = Device.init_from_file(
            di='1',
            class_name='EchoDevice',
            path=self.config_path
        )
        device_task = await wait_run_device(device)
        device2 = Device.init_from_file(
            di='2',
            class_name='EchoDevice',
            path=self.config_path
        )
        device2_task = await wait_run_device(device2)

        result = await device2.discovery_resource()

        di = device.get_device_id()

        await device2.observe(result[di].links['/oic/mnt'], device2.on_action)
        await asyncio.sleep(1)
        listening = device.get_param('/oic/con', 'listening')
        self.assertEqual(len(listening), 1, 'add observe')
        self.assertEqual(listening[0]['href'], '/oic/mnt')

        await device2.observe(result[di].links['/oic/mnt'])
        await asyncio.sleep(1)
        listening = device.get_param('/oic/con', 'listening')
        self.assertEqual(len(listening), 0, 'remove observe')
        device_task.cancel()
        device2_task.cancel()
        await device_task
        await device2_task


if __name__ == '__main__':
    unittest.main()
