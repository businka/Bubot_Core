import unittest
import logging
import asyncio
from unittest import IsolatedAsyncioTestCase
# from Bubot.Core.Coap.CoapServer2 import CoapServer
from Bubot_CoAP.messages.request import Request
from Bubot_CoAP.messages.response import Response
from BubotObj.OcfDevice.subtype.Device.Device import Device
from BubotObj.OcfDevice.subtype.EchoDevice.EchoDevice import EchoDevice as EchoDevice
from Bubot.Core.TestHelper import async_test, wait_run_device
from os import path


class TestDevice(IsolatedAsyncioTestCase):

    def setUp(self):
        logging.basicConfig()
        # _log = logging.getLogger('Bubot_CoAP.layers.message_layer')
        # _log.setLevel(logging.INFO)
        self.config_path = '{}/config/'.format(path.dirname(__file__))
        # self.device = Device.init_from_config()

    async def test_discovery_device(self):
        device0 = Device.init_from_file(
            di='10000000-0000-0000-0000-000000000001',
            class_name='EchoDevice',
            path=self.config_path
        )
        device_task = await wait_run_device(device0)

        # device = Device.init_from_config()
        # device_task = await wait_run_device(device)
        # a = device0.transport_layer.eps
        # await asyncio.sleep(10000)
        result = await device0.transport_layer.discovery_resource()
        di = device0.get_device_id()
        self.assertIn(di, result, 'device found')
        await device0.stop()
        self.assertTrue(device0.coap.endpoint['IPv6']['transport'].is_closing(), 'clossing coap')
        self.assertTrue(device0.coap.endpoint['multicast'][0]['transport'].is_closing(), 'run IPv6 transport')
        pass

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
