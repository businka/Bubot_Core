import asyncio
import logging
import unittest
from os import path
from unittest import IsolatedAsyncioTestCase

from bubot.core.TestHelper import wait_run_device
# from bubot.core.Coap.CoapServer2 import CoapServer
from bubot.buject.OcfDevice.subtype.Device.Device import Device

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger = logging.getLogger('Bubot_CoAP')
logger.setLevel(logging.INFO)
logger = logging.getLogger('aio_dtls')
logger.setLevel(logging.INFO)


class TestDevice(IsolatedAsyncioTestCase):

    def setUp(self):
        logging.basicConfig()
        # _log = logging.getLogger('Bubot_CoAP.layers.message_layer')
        # _log.setLevel(logging.INFO)
        self.config_path = '{}/config/'.format(path.dirname(__file__))
        # self.device = Device.init_from_config()

    async def asyncSetUp(self):
        pass

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

        logger = logging.getLogger('aio_dtls.protocol_dtls')
        logger.setLevel(logging.DEBUG)

        to = self.target

        server_uuid = self.device.get_device_id()
        obt_uuid = self.target['di']

        endpoint = self.device.transport_layer.get_endpoint(to, secure=True)

        to['href'] = '/oic/sec/doxm'
        oic_res = await self.device.transport_layer.send_message(
            'post',
            to,
            {'oxmsel': 0},
            timeout=10000
        )
        # res = self.send_with_dtlslib(to['coaps'])

        data = oic_res.decode_payload()

        to['href'] = '/oic/sec/pstat'
        response = await self.device.transport_layer.send_message(
            'post',
            to,
            {'om': 4},
            secure=True,
            timeout=10000,
        )

        #
        to['href'] = '/oic/sec/doxm'
        response = await self.device.transport_layer.send_message(
            'post',
            to,
            {'deviceuuid': obt_uuid},
            secure=True,
            timeout=10000
        )

        #
        to['href'] = '/oic/sec/doxm'
        response = await self.device.transport_layer.send_message(
            'post',
            to,
            {'rowneruuid': server_uuid},
            secure=True,
            timeout=10000
        )

        #
        to['href'] = '/oic/sec/acl2'
        response = await self.device.transport_layer.send_message(
            'post',
            to,
            {'rowneruuid': server_uuid},
            secure=True,
            timeout=10000
        )

        to['href'] = '/oic/sec/pstat'
        response = await self.device.transport_layer.send_message(
            'post',
            to,
            {'rowneruuid': server_uuid},
            secure=True,
            timeout=10000
        )

        to['href'] = '/oic/sec/cred'
        response = await self.device.transport_layer.send_message(
            'post',
            to,
            {'creds': [{'credtype': 1, 'subjectuuid': server_uuid,
                        'privatedata': {'encoding': 'oic.sec.encoding.raw', 'data': b''}}],
             'rowneruuid': server_uuid},
            secure=True,
            timeout=10000
        )

        to['href'] = '/oic/sec/sdi'
        response = await self.device.transport_layer.send_message(
            'post',
            to,
            {'uuid': '00000000-0000-0000-0000-000000000000', 'name': '', 'priv': False},
            secure=True,
            timeout=10000
        )
        to['href'] = '/oic/sec/doxm'
        response = await self.device.transport_layer.send_message(
            'post',
            to,
            {'owned': True},
            secure=True,
            timeout=10000,
        )
        from aio_dtls.tls.helper import Helper
        from uuid import UUID
        connection = endpoint.sock.connection_manager.get_connection(to['coaps'])

        identity_hint = UUID(obt_uuid).bytes
        psk = Helper.generate_owner_psk(
            connection, 'oic.sec.doxm.jw'.encode(), UUID(server_uuid).bytes, identity_hint)

        print('device uuid', UUID(obt_uuid).bytes.hex(" "))
        print('psk', psk.hex(" "))

        # await endpoint.send_alert()
        response = await self.device.transport_layer.send_message(
            'post',
            to,
            {'owned': True},
            secure=True,
            timeout=10000,
            identity_hint=UUID(obt_uuid).bytes,
            new_connection=dict(
                ciphers=['TLS_ECDHE_PSK_WITH_AES_128_CBC_SHA256'],
                psk=psk,
                identity_hint=identity_hint
            )
        )
        # import json
        # a = json.dumps(oic_res)

        await asyncio.sleep(10000)
        pass

    # def send_with_aiodtls(self, address):
    #     from aio_dtls import DtlsSocket
    #     s = DtlsSocket(
    #         socket.socket(socket.AF_INET, socket.SOCK_DGRAM),
    #         keyfile=None,
    #         certfile=None,
    #         #            cert_reqs=ssl.CERT_REQUIRED,
    #         ssl_version=ssl.PROTOCOL_DTLSv1_2,
    #         ca_certs=ISSUER_CERTFILE_EC,
    #         ciphers='ECDHE:EECDH',
    #         curves='prime256v1',
    #         sigalgs=None,
    #         user_mtu=None
    #     )

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

    def test_generate_shared_key(self):
        from aio_dtls.connection_manager.connection import Connection
        from aio_dtls.const.cipher_suites import CipherSuites as EnumCipherSuites
        from aio_dtls import math
        connection = Connection(("1", 1))
        connection.security_params.master_secret = b'\xe2\x99Bv(\xa2\xed\x07\x86\x91\xc6\xfd#\xa2e\xc0\xcf#\rb\xd76\xcap\xf2\xbd\x1f\xaa\x93\xe8*\xb8i\x1a!l\x86]<\xc8\xc1\xd0\xeb#r\x90\x08\x97'
        connection.security_params.client_random = b'a\xf3\n\xfa\xf6/F\xca\xc2\xf3\xed\x9b\x18\x7f&\xbf\xca?:\xddU\x10tjC\xde%25\xdah\xf0'
        connection.security_params.server_random = b'a\xf3\n\xfa3\xc0\xa6\x01\xf8 \xa9\x8c\x03\xc4bF\xd0\x0b\xa3\x11\x89\xa2-Z\x9a\x08\xcb.\xd2/\xa5\xeb'
        connection.security_params.cipher = EnumCipherSuites['TLS_ECDHE_PSK_WITH_AES_128_CBC_SHA256']
        server_uuid = b'\x10\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01'
        obt_uuid = b'\x08\xe7\x92\xf0\xa7\x05D-d~\xdd\xf0\x98\x112~'
        oxm = 'oic.sec.doxm.jw'.encode()

        # self.assertEqual('6F 69 63 2E 73 65 63 2E 64 6F 78 6D 2E 6A 77', oxm.hex(" ").upper())
        # self.assertEqual(
        #     '61 EE FF 05 0B 86 A1 2E A6 68 72 89 14 40 2E DF 94 C9 2A 40 2C EA 0B BE AD BE 3B 3D B7 A1 11 12 61 EE FF 05 DA 7D A1 AA 0B 6D 85 DE 64 C5 69 80 BD 99 C1 2F C6 DF FD 24 58 A8 03 5C 18 FE 5F CA',
        #     (connection.security_params.client_random + connection.security_params.server_random).hex(" ").upper())
        # self.assertEqual(
        #     '37 E1 82 4E 32 9C C7 6E 6F E9 8B 12 A0 C9 4C B4 1F FB 6B 81 98 90 42 D6 A2 7C D1 89 E5 18 91 F3 6D 34 74 EF 6C 92 94 CD 76 12 A2 77 EF 64 45 92',
        #     connection.security_params.master_secret.hex(" ").upper())

        # key_size = connection.cipher.cipher.key_material
        # iv_size = connection.cipher.cipher.iv_size
        # mac_key_len = connection.cipher.mac.mac_length
        # digestmod = connection.cipher.mac.digestmod
        #
        # key_block_len = 2 * (mac_key_len + key_size + iv_size);

        psk = math.p_hash(
            connection.digestmod,
            connection.security_params.master_secret,
            "key expansion".encode() + connection.security_params.client_random + connection.security_params.server_random,
            96
        )

        psk2 = math.p_hash2(
            connection.digestmod,
            connection.security_params.master_secret,
            [
                "key expansion".encode(),
                connection.security_params.client_random,
                connection.security_params.server_random
            ], 96
        )

        self.assertEqual(
            '6C C7 97 FA 1B 90 B9 2A F4 FC 38 C1 57 C6 A8 DE 18 A0 1C 61 BA 71 08 01 1F 90 EC E0 7F E7 73 BB FE 99 09 FA 5E FE E8 4B 1A 6E DB D2 D0 D2 CB 85 69 17 9A 9F 4D 72 44 45 ED AC C7 11 CB 70 EF 9B B5 39 0C 94 EC 90 42 D6 F9 2E 20 0B F3 F8 2A 3E 51 29 00 9C CD 2D F0 58 B3 90 85 5B B4 ED DB B0',
            psk.hex(" ").upper())

        self.assertEqual('64 5F 31 FE B8 E4 60 AE 8E 91 DA FA 29 BC D0 22', psk)

        a = 1


if __name__ == '__main__':
    unittest.main()

log = '''
<oc_tls_prf:1583>: msg hmac update:
<oc_tls_prf:1584>:  24 45 56 EE 12 4E 93 26 8C C1 B2 32 1F 8B 4C DE 80 70 28 38 88 BB 97 67 F7 B2 B5 45 1C E9 C8 08 CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC
<oc_tls_prf:1591>: msg hmac update:
<oc_tls_prf:1592>:  6B 65 79 20 65 78 70 61 6E 73 69 6F 6E
<oc_tls_prf:1595>: msg hmac update:
<oc_tls_prf:1596>:  64 17 FF 65 E3 13 BB 7C 1D 95 28 98 6C C0 81 DF DB E3 65 F1 D3 82 93 19 B9 AC 8C 8C D0 84 CC DC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC
<oc_tls_prf:1591>: msg hmac update:
<oc_tls_prf:1592>:  61 F0 27 A1 82 8E CA FA 24 CB D3 DD 3E 14 74 6E A7 36 11 08 5F C4 5C B5 C7 A1 7C 5E C2 30 6A D5
<oc_tls_prf:1595>: msg hmac update:
<oc_tls_prf:1596>:  6B 86 DF 1F 3D 7C 48 49 8A 10 18 97 72 AC 64 60 4B 42 BD AA 68 F0 6D BD 70 FA A4 61 9D 8C B2 21 CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC
<oc_tls_prf:1591>: msg hmac update:
<oc_tls_prf:1592>:  61 F0 27 A1 B4 BE F4 BD D0 3E 92 5C 8F 37 2E 7E F2 EA 93 B3 4C B6 17 2D 03 2C 15 28 6A 61 A6 85
<oc_tls_prf:1595>: msg hmac update:
<oc_tls_prf:1596>:  68 78 55 A9 01 15 7D B8 75 F6 9A A0 6F 2C 3E C2 EC F5 F0 0C 41 E7 7B 73 D6 D4 92 B0 54 8A B6 7D CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC
<oc_tls_prf:1600>: msg hmac update:
<oc_tls_prf:1601>:  8E 62 0D 77 EA C0 C6 C1 15 98 F1 FA 99 DF 90 D6 28 A7 12 0B 4F 29 C0 24 A8 E1 21 B5 9C C0 50 87 CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC
<oc_tls_prf:1623>: msg hmac update:
<oc_tls_prf:1624>:  CB 05 33 4A 0A EA 46 D4 27 39 C4 C1 27 A6 92 53 06 2A 6F 8B 92 A6 62 B8 AD 8D F4 03 74 1F BD 4B
<oc_tls_prf:1623>: msg hmac update:
<oc_tls_prf:1624>:  EA 72 29 BD 24 AB E9 73 D9 11 99 14 38 F7 BE C7 E0 56 8A 48 46 C7 70 CA 02 88 46 62 F8 C2 58 C0 CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC
<oc_tls_prf:1623>: msg hmac update:
<oc_tls_prf:1624>:  FC 72 26 62 BB 2A 2A A2 F6 C0 9F 3E CD 64 84 76 65 82 1C DC EC DC EF 00 70 46 2D 1A 4C F2 5F D8 CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC 03 00 00 00 00 00 00 00 20 00 00 00 00 00 00 00 60 00 00 00 20 00 00 00
<oc_tls_prf:1583>: msg hmac update:
<oc_tls_prf:1584>:  EF 6B 27 08 C2 A4 C0 A9 3A FD 68 9B 00 9C 86 2C 35 78 88 6B 5D 6B B3 5F 42 67 EE 28 FB CA FF E2 CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC
<oc_tls_prf:1591>: msg hmac update:
<oc_tls_prf:1592>:  6F 69 63 2E 73 65 63 2E 64 6F 78 6D 2E 6A 77
<oc_tls_prf:1595>: msg hmac update:
<oc_tls_prf:1596>:  0F 25 62 34 69 4E D0 23 21 24 32 5C 4C A9 4A 72 CD 1E A6 A3 7B 2C 0B B3 43 A1 02 7B C1 7D 62 78 CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC
<oc_tls_prf:1591>: msg hmac update:
<oc_tls_prf:1592>:  10 00 00 00 00 00 00 00 00 00 00 00 00 00 00 01
<oc_tls_prf:1595>: msg hmac update:
<oc_tls_prf:1596>:  F4 B3 73 94 80 95 02 B9 84 5F 4C E4 47 E2 F9 97 7C 8B 03 EA 20 7E 5C 8F CA 47 62 42 86 0B 0E F7 CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC
<oc_tls_prf:1591>: msg hmac update:
<oc_tls_prf:1592>:  29 BB 99 AA 2F CF 42 95 52 10 15 92 79 46 5B 92
<oc_tls_prf:1595>: msg hmac update:
<oc_tls_prf:1596>:  88 02 34 42 AC C1 03 AA A5 9E DE DD A6 C3 63 C4 97 9C 7C 15 BD AC F5 19 AC 29 CA 76 9D 06 CB 86 CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC
<oc_tls_prf:1600>: msg hmac update:
<oc_tls_prf:1601>:  E0 EE BA DE D0 52 A6 4D 8A 4E 5F 8B 43 8E 7E 0C 1F 2B 35 4B C4 13 44 47 50 22 09 2C 50 6A 8E 6F CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC CC
<oc_tls_prf:1623>: msg hmac update:
<oc_tls_prf:1624>:  A6 E0 1F 9F 13 48 C3 2B F6 4B 15 D4 30 D5 EF A6
<oc_sec_derive_owner_psk:1731>: oc_tls: oxm:
<oc_sec_derive_owner_psk:1732>:  6F 69 63 2E 73 65 63 2E 64 6F 78 6D 2E 6A 77
<oc_sec_derive_owner_psk:1733>: oc_tls: label:
<oc_sec_derive_owner_psk:1734>:  6B 65 79 20 65 78 70 61 6E 73 69 6F 6E
<oc_sec_derive_owner_psk:1735>: oc_tls: obt_uuid:
<oc_sec_derive_owner_psk:1736>:  10 00 00 00 00 00 00 00 00 00 00 00 00 00 00 01
<oc_sec_derive_owner_psk:1737>: oc_tls: server_uuid:
<oc_sec_derive_owner_psk:1739>:  29 BB 99 AA 2F CF 42 95 52 10 15 92 79 46 5B 92
<oc_sec_derive_owner_psk:1741>: oc_tls: master secret:
<oc_sec_derive_owner_psk:1742>:  8D AA 98 36 1C 42 B9 54 39 14 27 FB 7E 06 F6 B4 55 76 AF 54 D5 F8 92 E5 DA 31 44 6C 0C 4C D4 EB 72 65 90 EE 75 67 92 06 C9 0E AC F6 EE A2 39 B2
<oc_sec_derive_owner_psk:1743>: oc_tls: client_server_random:
<oc_sec_derive_owner_psk:1744>:  61 F0 27 A1 B4 BE F4 BD D0 3E 92 5C 8F 37 2E 7E F2 EA 93 B3 4C B6 17 2D 03 2C 15 28 6A 61 A6 85 61 F0 27 A1 82 8E CA FA 24 CB D3 DD 3E 14 74 6E A7 36 11 08 5F C4 5C B5 C7 A1 7C 5E C2 30 6A D5
<oc_sec_derive_owner_psk:1745>: oc_tls: key_block
<oc_sec_derive_owner_psk:1746>:  CB 05 33 4A 0A EA 46 D4 27 39 C4 C1 27 A6 92 53 06 2A 6F 8B 92 A6 62 B8 AD 8D F4 03 74 1F BD 4B EA 72 29 BD 24 AB E9 73 D9 11 99 14 38 F7 BE C7 E0 56 8A 48 46 C7 70 CA 02 88 46 62 F8 C2 58 C0 FC 72 26 62 BB 2A 2A A2 F6 C0 9F 3E CD 64 84 76 65 82 1C DC EC DC EF 00 70 46 2D 1A 4C F2 5F D8
<oc_sec_derive_owner_psk:1747>: oc_tls: PSK
<oc_sec_derive_owner_psk:1748>:  A6 E0 1F 9F 13 48 C3 2B F6 4B 15 D4 30 D5 EF A6
'''
