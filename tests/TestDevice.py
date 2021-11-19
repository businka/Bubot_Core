import unittest
from unittest import IsolatedAsyncioTestCase
from Bubot_CoAP.messages.response import Response
from BubotObj.OcfDevice.subtype.Device.Device import Device
from BubotObj.OcfDevice.subtype.EchoDevice.EchoDevice import EchoDevice as EchoDevice
from Bubot.Core.TestHelper import async_test, wait_run_device
from os import path
import asyncio
import logging
from Bubot_CoAP import defines
from Bubot_CoAP.messages.request import Request
from Bubot_CoAP.messages.numbers import NON, Code

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


class TestDevice(IsolatedAsyncioTestCase):

    def setUp(self):
        logging.basicConfig()
        # _log = logging.getLogger('Bubot_CoAP.layers.message_layer')
        _log = logging.getLogger('Bubot_CoAP')
        _log.setLevel(logging.DEBUG)
        self.config_path = '{}/config/'.format(path.dirname(__file__))
        # self.device = Device.init_from_config()

    async def test_init(self):
        device = Device.init_from_file(
            di='10000000-0000-0000-0000-000000000001',
            class_name='EchoDevice',
            path=self.config_path
        )
        res, response = await device.res['/oic/res'].render_GET_advanced(Request(), Response())
        request = Request()
        request.query = {'rt': ['oic.r.doxm']}
        res, response = await device.res['/oic/res'].render_GET_advanced(request, Response())
        self.assertTrue(isinstance(device, EchoDevice), 'instance')
        self.assertEqual(device.get_param('/oic/p', 'mnpv'), Device.version, 'platform version ')
        self.assertEqual(device.get_param('/oic/d', 'sv'), device.version, 'device version')
        self.assertEqual(device.get_param('/oic/d', 'dmno'), EchoDevice.__name__, 'device class')
        self.assertEqual(device.get_param('/oic/d', 'di'), '10000000-0000-0000-0000-000000000001', 'di')
        self.assertEqual(device.get_param('/oic/con', 'udpCoapPort'), 11111, 'coap port from file')

        device = EchoDevice.init_from_file(
            di='10000000-0000-0000-0000-000000000001',
            path='{}/config/'.format(path.dirname(__file__))
        )
        self.assertTrue(isinstance(device, EchoDevice), 'instance')
        self.assertEqual(device.get_param('/oic/p', 'mnpv'), Device.version, 'platform version ')
        self.assertEqual(device.get_param('/oic/d', 'sv'), device.version, 'device version')
        self.assertEqual(device.get_param('/oic/d', 'dmno'), EchoDevice.__name__, 'device class')
        self.assertEqual(device.get_param('/oic/d', 'di'), '10000000-0000-0000-0000-000000000001', 'di')
        self.assertEqual(device.get_param('/oic/con', 'udpCoapPort'), 11111, 'coap port from file')

        pass

    async def test_save_config(self):
        device = Device.init_from_file(
            di='10000000-0000-0000-0000-000000000001',
            class_name='EchoDevice',
            path=self.config_path
        )
        new_id = '3'
        device.set_device_id(new_id)
        data = device.save_config()
        self.assertEqual(data[1]['/oic/d']['di'], new_id)
        self.assertEqual(data[1]['/oic/d']['di'], new_id)
        self.assertEqual(data[1]['/oic/sec/doxm']['deviceuuid'], new_id)
        pass

    async def test_run_coap_with_a_known_port_number(self):
        device = Device.init_from_file(
            di='10000000-0000-0000-0000-000000000001',
            class_name='EchoDevice',
            path=self.config_path
        )
        port = device.get_param('/oic/con', 'udpCoapPort')
        await device.transport_layer.start()
        unicast_endpoints = device.transport_layer.coap.endpoint_layer.unicast_endpoints
        # self.assertIn('::', unicast_endpoints)
        # self.assertIn(port, unicast_endpoints['::'])
        # self.assertIn('', unicast_endpoints)
        # self.assertIn(port, unicast_endpoints[''])
        await device.transport_layer.stop()
        self.assertFalse(unicast_endpoints)
        pass

    async def test_run_coap_without_port_number(self):
        device = Device.init_from_config()
        self.assertEqual(device.get_param('/oic/con', 'udpCoapPort'), 0)
        await device.transport_layer.start()
        self.assertTrue(device.get_param('/oic/con', 'udpCoapPort') > 0)
        eps_ipv4 = device.transport_layer.eps_coap_ipv4
        self.assertTrue(device.transport_layer.eps_coap_ipv4, 'dont run IPv4 transport')
        first_ip = list(eps_ipv4)[0]
        eps_ipv4_first_ip = eps_ipv4[first_ip]
        first_port = list(eps_ipv4_first_ip)[0]
        ep = eps_ipv4_first_ip[first_port]
        self.assertTrue(device.transport_layer.eps_coap_ipv4, 'dont run IPv4 transport')
        self.assertFalse(ep.transport.is_closing(), 'run IPv4 transport')

        await device.transport_layer.stop()

        self.assertTrue(ep.transport.is_closing(), 'IPv4 transport dont close')
        pass

    async def test_run_stop_device(self):
        device = Device.init_from_file(
            di='10000000-0000-0000-0000-000000000001',
            class_name='EchoDevice',
            path=self.config_path
        )
        await wait_run_device(device)
        eps = device.transport_layer.eps_coap_ipv6
        ip_eps = eps[list(eps.keys())[0]]
        ep = ip_eps[list(ip_eps.keys())[0]]
        transport = ep.transport
        self.assertFalse(transport.is_closing(), 'closing coap')
        await device.stop()
        self.assertTrue(transport.is_closing(), 'closing coap')
        pass

    async def test_device_request(self):
        device0 = Device.init_from_file(
            di='10000000-0000-0000-0000-000000000001',
            class_name='EchoDevice',
            path=self.config_path
        )
        await wait_run_device(device0)

        device1 = Device.init_from_file(
            di='20000000-0000-0000-0000-000000000002',
            class_name='EchoDevice',
            path=self.config_path
        )
        await wait_run_device(device1)
        address = list(device0.transport_layer.eps_coap_ipv4.keys())[0]
        request = Request()
        # request.token = _token
        # request.query = {'owned': ['TRUE']}
        request.type = NON
        request.code = Code.GET
        request.uri_path = '/oic/res'
        request.content_type = 10000
        request.source = (address, list(device0.transport_layer.eps_coap_ipv4[address].keys())[0])
        # request.multicast = True
        # request.family = _msg.family
        request.scheme = 'coap'
        request.destination = (address, list(device1.transport_layer.eps_coap_ipv4[address].keys())[0])
        res2 = await device0.transport_layer.coap.send_message(request)
        links = res2.decode_payload()
        await device0.stop()
        await device1.stop()
        self.assertGreater(len(links), 7)
        link = links[0]
        self.assertIn('href', link)
        self.assertIn('eps', link)
        pass

    async def test_device_self_get_request(self):
        defines.EXCHANGE_LIFETIME = 2
        device0 = Device.init_from_file(
            di='10000000-0000-0000-0000-000000000001',
            class_name='EchoDevice',
            path=self.config_path
        )
        await wait_run_device(device0)

        address = list(device0.transport_layer.eps_coap_ipv4.keys())[0]
        request = Request()
        # request.token = _token
        # request.query = {'owned': ['TRUE']}
        request.type = NON
        request.code = Code.GET
        request.uri_path = '/oic/res'
        request.content_type = 10000
        request.source = (address, list(device0.transport_layer.eps_coap_ipv4[address].keys())[0])
        # request.multicast = True
        # request.family = _msg.family
        request.scheme = 'coap'
        request.destination = (address, list(device0.transport_layer.eps_coap_ipv4[address].keys())[0])
        # request.destination = (address, 5683)
        res2 = await device0.transport_layer.coap.send_message(request)
        links = res2.decode_payload()
        await asyncio.sleep(15)
        await device0.stop()
        self.assertGreater(len(links), 7)
        link = links[0]
        self.assertIn('href', link)
        self.assertIn('eps', link)
        pass

    async def test_device_self_handshake(self):
        defines.EXCHANGE_LIFETIME = 2
        device0 = Device.init_from_file(
            di='10000000-0000-0000-0000-000000000001',
            class_name='EchoDevice',
            path=self.config_path
        )
        await wait_run_device(device0)
        ep = device0.transport_layer.coap.endpoint_layer.find_endpoint(scheme='coaps')
        to = {
            'net_interface': ep.address[0],
            'coaps': ep.address,
            'family': ep.family
        }
        res = await device0.transport_layer.send_raw_data(
            to,
            b'\x16\xfe\xfd\x00\x00\x00\x00\x00\x00\x00\x02\x00b\x01\x00\x00V\x00\x00\x00\x00\x00\x00\x00V\xfe\xfd`\xc6_,\xdc\x0b&\xcf1L\x98\x15%\xcc\xd6\xf5\xba\xb4\xb5\x93\xd39\rk\xfb\x16l\xf0\xdd\xd9,a\x00\x00\x00\x04\xff\x00\x00\xff\x01\x00\x00(\x00\r\x00\x12\x00\x10\x06\x03\x06\x01\x05\x03\x05\x01\x04\x03\x04\x01\x03\x03\x03\x01\x00\n\x00\x04\x00\x02\x00\x17\x00\x0b\x00\x02\x01\x00\x00\x17\x00\x00',
            secure=True
        )
        await asyncio.sleep(10000)

        pass

    async def test_device_self_post_request(self):
        defines.EXCHANGE_LIFETIME = 2
        device0 = Device.init_from_file(
            di='10000000-0000-0000-0000-000000000001',
            class_name='EchoDevice',
            path=self.config_path
        )
        await wait_run_device(device0)

        address = list(device0.transport_layer.eps_coap_ipv4.keys())[0]
        request = Request()
        # request.token = _token
        # request.query = {'owned': ['TRUE']}
        request.type = NON
        request.code = Code.POST
        request.uri_path = '/oic/sec/doxm'
        request.content_type = 10000
        request.source = (address, list(device0.transport_layer.eps_coap_ipv4[address].keys())[0])
        # request.multicast = True
        # request.family = _msg.family
        request.encode_payload({'oxmsel': 0})
        request.scheme = 'coap'
        request.destination = (address, list(device0.transport_layer.eps_coap_ipv4[address].keys())[0])
        # request.destination = (address, 5683)
        res2 = await device0.transport_layer.coap.send_message(request)
        links = res2.decode_payload()
        await asyncio.sleep(15)
        await device0.stop()
        self.assertGreater(len(links), 7)
        link = links[0]
        self.assertIn('href', link)
        self.assertIn('eps', link)
        pass

    async def test_discovery_device2(self):
        device0 = Device.init_from_file(
            di='20000000-0000-0000-0000-000000000002',
            class_name='EchoDevice',
            path=self.config_path
        )
        device_task = await wait_run_device(device0)

        # device = Device.init_from_config()
        # device_task = await wait_run_device(device)
        # a = device0.transport_layer.eps
        await asyncio.sleep(10000)
        # result = await device0.transport_layer.discovery_resource()
        # di = device0.get_device_id()
        # self.assertIn(di, result, 'device found')
        # await device0.stop()
        # self.assertTrue(device0.coap.endpoint['IPv6']['transport'].is_closing(), 'clossing coap')
        # self.assertTrue(device0.coap.endpoint['multicast'][0]['transport'].is_closing(), 'run IPv6 transport')
        pass

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
