import asyncio
import logging
import unittest
from os import path

from Bubot.Helpers.ArrayHelper import ArrayHelper

from Bubot.Core.TestHelper import async_test, wait_run_device
# from bubot.CoapServer import CoapServer
from BubotObj.OcfDevice.subtype.Device.Device import Device
from BubotObj.OcfDevice.subtype.EchoDevice.EchoDevice import EchoDevice as EchoDevice


class TestDevice(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.DEBUG)
        self.config_path = path.dirname(__file__)
        # self.device = Device.init_from_config()

    @async_test
    async def test_init(self):
        device = Device.init_from_file(
            di='e0000000-0000-0000-0000-000000000001',
            class_name='EchoDevice',
            path=self.config_path
        )
        self.assertTrue(isinstance(device, EchoDevice), 'instance')
        self.assertEqual(device.get_param('/oic/p', 'mnpv'), Device.version, 'platform version ')
        self.assertEqual(device.get_param('/oic/d', 'sv'), device.version, 'device version')
        self.assertEqual(device.get_param('/oic/d', 'dmno'), EchoDevice.__name__, 'device class')
        self.assertEqual(device.get_param('/oic/d', 'di'), 'e0000000-0000-0000-0000-000000000001', 'di')
        self.assertEqual(device.get_param('/oic/con', 'udpCoapPort'), 11111, 'coap port from file')

        device = EchoDevice.init_from_file(
            di='e0000000-0000-0000-0000-000000000001',
            path=path.join(path.dirname(__file__), 'conf')
        )
        self.assertTrue(isinstance(device, EchoDevice), 'instance')
        self.assertEqual(device.get_param('/oic/p', 'mnpv'), Device.version, 'platform version ')
        self.assertEqual(device.get_param('/oic/d', 'sv'), device.version, 'device version')
        self.assertEqual(device.get_param('/oic/d', 'dmno'), EchoDevice.__name__, 'device class')
        self.assertEqual(device.get_param('/oic/d', 'di'), 'e0000000-0000-0000-0000-000000000001', 'di')
        self.assertEqual(device.get_param('/oic/con', 'udpCoapPort'), 11111, 'coap port from file')

        pass

    @async_test
    async def test_save_config(self):
        device = Device.init_from_file(
            di='e0000000-0000-0000-0000-000000000001',
            class_name='EchoDevice',
            path=self.config_path
        )
        device.set_device_id('e0000000-0000-0000-0000-000000000003')
        data = device.save_config()
        self.assertEqual(data[1]['/oic/d']['di'], 'e0000000-0000-0000-0000-000000000003')
        pass

    @async_test
    async def test_run_coap_with_a_known_port_number(self):
        device = Device.init_from_file(
            di='e0000000-0000-0000-0000-000000000001',
            class_name='EchoDevice',
            path=self.config_path
        )
        await device.transport_layer.start()
        self.assertFalse(device.coap.endpoint['IPv4'], 'dont run IPv4 transport')
        self.assertFalse(device.coap.endpoint['IPv6']['transport'].is_closing(), 'run IPv6 transport')
        self.assertFalse(device.coap.endpoint['multicast'][0]['transport'].is_closing(), 'run IPv6 transport')
        device.coap.close()
        self.assertTrue(device.coap.endpoint['IPv6']['transport'].is_closing(), 'clossing coap')
        self.assertEqual(device.coap.unicast_port, device.get_param('/oic/con', 'udpCoapPort'),
                         'init coap with exist port')
        pass

    @async_test
    async def test_run_coap_without_port_number(self):
        device = Device.init_from_config()
        await device.transport_layer.start()

        self.assertFalse(device.coap.endpoint['IPv4'], 'dont run IPv4 transport')
        self.assertFalse(device.coap.endpoint['IPv6']['transport'].is_closing(), 'run IPv6 transport')
        self.assertFalse(device.coap.endpoint['multicast'][0]['transport'].is_closing(), 'run IPv6 transport')

        device.coap.close()

        self.assertTrue(device.coap.endpoint['IPv6']['transport'].is_closing(), 'clossing coap')
        self.assertTrue(device.coap.endpoint['multicast'][0]['transport'].is_closing(), 'run IPv6 transport')
        self.assertEqual(device.coap.unicast_port, device.get_param('/oic/con', 'udpCoapPort'), 'init new coap port')
        pass

    @async_test
    async def test_discovery_device(self):
        device = Device.init_from_config()
        device_task = await wait_run_device(device)
        result = await device.transport_layer.discovery_resource()
        di = device.get_device_id()
        self.assertIsNot(ArrayHelper.find_by_key(result, di, 'di'), -1)
        device_task.cancel()
        await device_task
        self.assertEquals(len(device.transport_layer.eps_coap_ipv4), 0, 'clossing coap ipv4')
        self.assertEquals(len(device.transport_layer.eps_coap_ipv6), 0, 'clossing coap ipv6')
        pass

    @async_test
    async def test_observe_device(self):
        device = Device.init_from_file(
            di='e0000000-0000-0000-0000-000000000001',
            class_name='EchoDevice',
            path=self.config_path
        )
        device_task = await wait_run_device(device)
        device2 = Device.init_from_file(
            di='e0000000-0000-0000-0000-000000000002',
            class_name='EchoDevice',
            path=self.config_path
        )
        device2_task = await wait_run_device(device2)

        result = await device2.transport_layer.discovery_resource()

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
