import asyncio
import logging
import unittest
from os import path

from bubot.core.TestHelper import wait_run_device
from bubot.OcfResource.OcfResource import OcfResource
# from bubot.CoapServer import CoapServer
from bubot.buject.OcfDevice.subtype.Device.Device import Device
from bubot.buject.OcfDevice.subtype.Device.RedisQueueMixin import RedisQueueMixin


class TestRedisQueue(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        logging.basicConfig(level=logging.DEBUG)
        self.config_path = path.dirname(__file__)
        self.config = [
            {
                "/oic/d": {
                    "piid": "70000000-0000-0000-0000-000000000000",
                    "di": "70000000-0000-0000-0000-000000000000"
                },
                "/oic/con": {
                    "redis_url": "redis://192.168.1.77/11",
                    "udpCoapIPv4Ssl": None
                },
                "/test_queue": {
                    "rt": ["bubot.redis.queue"]
                }
            },
            {
                "/oic/d": {
                    "piid": "70000000-0000-0000-0000-000000000001",
                    "di": "70000000-0000-0000-0000-000000000001"
                },
                "/oic/con": {
                    "redis_url": "redis://192.168.1.77/11",
                    "udpCoapIPv4Ssl": None
                },
            }
        ]

        self.device0 = RedisTestDevice().init(self.config[0])
        self.device0_task = await wait_run_device(self.device0)

        self.device1 = RedisTestDevice().init(self.config[1])
        self.device1_task = await wait_run_device(self.device1)

    async def asyncTearDown(self) -> None:
        self.device0_task.cancel()
        self.device1_task.cancel()
        await self.device0_task
        await self.device1_task

    async def test_good_request(self):
        res = await self.device1.execute_in_redis_queue('/test_queue', 2)
        self.assertEqual(5, res)
        pass

    async def test_good_request_with_callback(self):
        res = await self.device1.execute_in_redis_queue('/test_queue', 2, self.device1.callback)
        self.assertEqual(5, res)
        pass


    async def test_exception_in_answer(self):
        res = await self.device1.execute_in_redis_queue('/test_queue', 0)
        self.assertEqual(5, res)


class TestRedisQueueResource(OcfResource):
    async def render_POST_advanced(self, request, response):
        response = request.generate_answer(10 / request.cn)
        return self, response


class RedisTestDevice(RedisQueueMixin, Device):
    def __init__(self, **kwargs):
        Device.__init__(self, **kwargs)
        RedisQueueMixin.__init__(self, **kwargs)
        self.resource_layer.add_handler('/test_queue', TestRedisQueueResource)

    async def on_pending(self):
        await RedisQueueMixin.on_pending(self)
        await Device.on_pending(self)
        pass

    async def on_cancelled(self):
        await RedisQueueMixin.on_cancelled(self)
        await Device.on_cancelled(self)

    async def on_idle(self):
        await Device.on_idle(self)
        pass

    async def callback(self, value):
        return value * 10

    @staticmethod
    def device_process(class_name, di, queue, kwargs):
        h = logging.handlers.QueueHandler(queue)  # Just the one handler needed
        kwargs['loop'] = asyncio.new_event_loop()
        asyncio.set_event_loop(kwargs['loop'])
        root = logging.getLogger()
        root.handlers = []
        root.addHandler(h)
        device = Device.init_from_file(
            class_name=class_name,
            di=di,
            **kwargs
        )
        device.run()


if __name__ == '__main__':
    unittest.main()
