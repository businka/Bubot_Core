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

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


class TestDevice(IsolatedAsyncioTestCase):

    def setUp(self):
        logging.basicConfig()
        # _log = logging.getLogger('Bubot_CoAP.layers.message_layer')
        # _log.setLevel(logging.INFO)
        self.config_path = '{}/config/'.format(path.dirname(__file__))
        # self.device = Device.init_from_config()

    async def asyncSetUp(self):
        self.device = Device.init_from_file(
            di='10000000-0000-0000-0000-000000000001',
            class_name='EchoDevice',
            path=self.config_path
        )
        self.device_task = await wait_run_device(self.device)
        self.devices = await self.device.transport_layer.discovery_resource(filter={'oic/d': [{'n': 'Lamp'}]},
                                                                            timeout=3)
        self.target = None
        for device in self.devices:
            if device['n'] == 'Lamp':
                self.target = device
                break
        if self.target is None:
            raise Exception('iotivity not found. please run SimpleServer')
        a = 1

    async def asyncTearDown(self):
        await self.device.stop()

    async def test_oic_res(self):
        to = self.target
        to['href'] = '/oic/res'
        oic_res = await self.device.transport_layer.send_message(
            'retrieve',
            to,
        )
        import json
        a = json.dumps(oic_res)
        pass

    async def test_just_works_otm(self):
        logger = logging.getLogger('aio_dtls.protocol_dtls')
        logger.setLevel(logging.DEBUG)
        to = self.target
        to['href'] = '/oic/sec/doxm'
        oic_res = await self.device.transport_layer.send_message(
            'post',
            to,
            {'oxmsel': 0},
            timeout=10000
        )
        # res = self.send_with_dtlslib(to['coaps'])

        data = oic_res.decode_payload()
        res = await self.device.transport_layer.send_raw_data(
            to,
            'hello',
            secure=True
        )
        # import json
        # a = json.dumps(oic_res)
        await asyncio.sleep(10000)
        pass

    def send_with_aiodtls(self, address):
        from aio_dtls import DtlsSocket
        s = DtlsSocket(
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM),
            keyfile=None,
            certfile=None,
            #            cert_reqs=ssl.CERT_REQUIRED,
            ssl_version=ssl.PROTOCOL_DTLSv1_2,
            ca_certs=ISSUER_CERTFILE_EC,
            ciphers='ECDHE:EECDH',
            curves='prime256v1',
            sigalgs=None,
            user_mtu=None
        )
    def send_with_dtlslib(self, address):
        from os import path
        import ssl
        from logging import basicConfig, DEBUG
        basicConfig(level=DEBUG)  # set now for dtls import code
        from dtls import do_patch
        from dtls.wrapper import DtlsSocket
        import socket
        import os

        do_patch()
        ISSUER_CERTFILE_EC = os.path.join(os.path.dirname(__file__) or os.curdir, "certs", "ca-cert_ec.pem")
        cert_path = path.join(path.abspath(path.dirname(__file__)), "certs")
        s = DtlsSocket(
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM),
            keyfile=None,
            certfile=None,
            #            cert_reqs=ssl.CERT_REQUIRED,
            ssl_version=ssl.PROTOCOL_DTLSv1_2,
            ca_certs=ISSUER_CERTFILE_EC,
            ciphers='ECDHE:EECDH',
            curves='prime256v1',
            sigalgs=None,
            user_mtu=None
        )
        s.connect(address)
        s.send('Hi there'.encode())
        print(s.recv().decode())
        s = s.unwrap()
        s.close()


if __name__ == '__main__':
    unittest.main()
