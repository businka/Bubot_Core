# from bubot.CoapServer import CoapServer
import asyncio
import logging
import unittest
from uuid import uuid4

from bubot.buject.OcfDevice.subtype.Device.Device import Device
from bubot.buject.User.User import User
from bubot.core.DataBase.Mongo import Mongo as Storage
from bubot.core.DeviceLink import DeviceLink
from bubot.core.TestHelper import wait_run_device, wait_cancelled_device
from bubot_helpers.ArrayHelper import ArrayHelper

logging.basicConfig()
# logger = logging.getLogger()
# logger.setLevel(logging.DEBUG)
logger = logging.getLogger('bubot')
logger.setLevel(logging.DEBUG)
logger = logging.getLogger('Bubot_CoAP')
logger.setLevel(logging.INFO)


class TestDeviceOBT(unittest.IsolatedAsyncioTestCase):
    net_interface = "192.168.1.11"
    config = {
        "/oic/con": {
            "logLevel": "info",
            "port": 8088,
            "udpCoapIPv4Ssl": True
        }
    }
    echo_config = {
        "/oic/con": {
            "logLevel": "debug",
            "udpCoapIPv4Ssl": True
        }
    }

    async def asyncSetUp(self) -> None:
        self.storage = await Storage.connect()
        self.user = User(self.storage)
        await self.user.find_user_by_auth('password', 'razgovorov')

    async def asyncTearDown(self) -> None:
        await wait_cancelled_device(self.echo, self.echo_task)
        await wait_cancelled_device(self.device, self.device_task)

    async def test_ownership(self):
        new_di = "00000000-0000-0000-0000-000000000003"
        disposable_access_token = str(uuid4())
        await self.user.update_auth({'type': 'ocf_reg_device', 'id': new_di, 'value': disposable_access_token})

        self.device = Device.init_from_config(self.config,
                                              di="00000000-0000-0000-0000-000000000001",
                                              class_name='WebServer')
        self.device_task = await wait_run_device(self.device)

        self.echo = Device.init_from_config(self.echo_config,
                                            di="00000000-0000-0000-0000-000000000002",
                                            class_name='EchoDevice')
        self.echo_task = await wait_run_device(self.echo)

        result = await self.device.transport_layer.discovery_resource(owned=False, timeout=15)
        di = self.echo.get_device_id()
        echo_data_link = ArrayHelper.find_by_key(result, di, 'di')
        self.assertIsNot(echo_data_link, -1)
        echo_link = DeviceLink(result[echo_data_link])

        await echo_link.device_ownership(self.device, self.user.obj_id, new_di=new_di,
                                         cis='coap+tcp://192.168.1.11:8777', sid=disposable_access_token)
        sid = self.echo.get_param('/CoAPCloudConfResURI', 'sid')
        self.assertTrue(bool(sid))
        cloud_access_token = None
        i = 0
        for i in range(5):
            try:
                cloud_access_token = self.echo.get_cloud_access_token()
                break
            except Exception as err:
                await asyncio.sleep(5)
        self.assertIsNotNone(cloud_access_token)
        sid = self.echo.get_param('/CoAPCloudConfResURI', 'sid')
        self.assertFalse(bool(sid))
        # self.device_task.cancel()
        # await self.device_task
        self.assertEquals(len(self.device.transport_layer.eps_coap_ipv4), 0, 'closing coap ipv4')
        self.assertEquals(len(self.device.transport_layer.eps_coap_ipv6), 0, 'closing coap ipv6')
        pass

    async def test_register(self):
        new_di = "00000000-0000-0000-0000-000000000003"
        disposable_access_token = str(uuid4())
        await self.user.update_auth({'type': 'ocf_reg_device', 'id': new_di, 'value': disposable_access_token})

        self.device = Device.init_from_config(self.config,
                                              di="00000000-0000-0000-0000-000000000001",
                                              class_name='WebServer')
        self.device_task = await wait_run_device(self.device)

        self.user = User(self.storage)

        new_di = "00000000-0000-0000-0000-000000000003"
        disposable_access_token = str(uuid4())
        await self.user.update_auth({'type': 'ocf_reg_device', 'id': new_di, 'value': disposable_access_token})

        await self.user.find_user_by_auth('password', 'razgovorov')
        self.echo = Device.init_from_config(self.echo_config,
                                            di="00000000-0000-0000-0000-000000000002",
                                            class_name='EchoDevice')
        self.echo_task = await wait_run_device(self.echo)
        echo_link = DeviceLink(self.echo.get_link())
        await echo_link.add_to_cloud(self.device, self.user)
        await self.echo_task


if __name__ == '__main__':
    unittest.main()
