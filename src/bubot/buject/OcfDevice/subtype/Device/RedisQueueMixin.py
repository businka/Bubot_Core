import asyncio
from uuid import uuid4

import aioredis
import bson

from Bubot.Helpers.ExtException import ExtException, ExtNotImplemented
from Bubot.Ocf.OcfMessage import OcfMessage, OcfRequest as Request, OcfResponse as Response


class RedisQueueMixin:
    def __init__(self, **kwargs):
        self.redis_url = None
        self.redis_queues = []
        self.redis = None
        self._redis_waited_answer = {}
        self.redis_queue_worker_task = None
        self.current_redis_msg = None

    async def on_pending(self):
        self.redis_url = self.get_param('/oic/con', 'redis_url', None)
        if not self.redis_url:
            return
        self.redis_queues = [self.get_device_id()]
        for href in self.data:
            if 'bubot.redis.queue' in self.data[href].get('rt', []):
                self.redis_queues.append(href)

        self.log.info(f'Connect {self.redis_url} {self.redis_queues}')
        try:
            self.redis = await aioredis.from_url(self.redis_url)
        except Exception as err:
            err1 = ExtException(parent=err)
            self.log.error(err1)
            raise err1 from err
        self.redis_queue_worker_task = self.loop.create_task(self.run_redis_queue_worker())

    async def on_cancelled(self):
        if self.redis_queue_worker_task:
            self.redis_queue_worker_task.cancel()
            await self.redis_queue_worker_task
        if self.redis:
            await self.redis.close()

    async def run_redis_queue_worker(self):
        while True:
            try:
                self.current_redis_msg = None
                res = await self.redis.brpop(self.redis_queues, 30)
                if res:
                    queue, data = res
                    try:
                        self.current_redis_msg = OcfMessage.init_from_bson(data)

                        if isinstance(self.current_redis_msg, Request):
                            href = self.current_redis_msg.parse_url_to().path
                            try:
                                res = self.res[href]
                            except KeyError:
                                response = self.current_redis_msg.generate_error(ExtNotImplemented())
                                await self.send_response(response)
                                continue
                            try:
                                self.log.debug(f'execute {self.current_redis_msg.ri} in redis queue {queue}')
                                res, response = await getattr(res, 'render_POST_advanced')(
                                    request=self.current_redis_msg, response=None)

                            except Exception as err:
                                response = self.current_redis_msg.generate_error(ExtException(parent=err))
                            await self.send_response(response)
                            pass

                        elif isinstance(self.current_redis_msg, Response):
                            self.log.debug(f'set result {self.current_redis_msg.ri} in redis queue {queue}')
                            self.set_result_to_redis_queue_request(self.current_redis_msg)
                    except Exception as err:
                        self.log.error(ExtException(parent=err))
            except asyncio.CancelledError:
                # if self.current_redis_msg:  # todo  помещать необработанное сообщение обратно в редис
                return

            except Exception as err:
                self.log.error(ExtException(parent=err))
                return

    async def execute_in_redis_queue(self, href, data=None):
        src_redis = self.get_device_id()
        request = Request(
            fr=f"redis://{src_redis}",
            to=f"redis://{href}",
            op='update',
            ri=str(uuid4()),
            cn=data
        )
        raw_data = bson.encode(request.to_dict())
        self.log.info(f'send request {request.ri} in redis queue {href}')
        await self.redis.rpush(href, raw_data)
        waiter = Waiter(request)
        self._redis_waited_answer[waiter.key] = waiter
        return waiter

    async def execute_in_redis_queue_sync(self, href, data=None, *, timeout=None):
        waiter = await self.execute_in_redis_queue(href, data)
        return await self.wait_redis_request_from_queue(waiter, timeout=timeout)

    async def send_response(self, response: Response):
        href = response.parse_url_to().hostname
        raw_data = bson.encode(response.to_dict())
        self.log.debug(f'send response {response.ri} to redis queue {href}')
        await self.redis.rpush(href, raw_data)

    async def wait_redis_request_from_queue(self, waiter, *, timeout=None):
        try:
            response = await asyncio.wait_for(waiter.future, timeout)
            if response.is_successful():
                return response.cn
            else:
                raise ExtException(parent=response.cn)
        except asyncio.CancelledError:
            waiter.future.set_exception(asyncio.CancelledError())
        except asyncio.TimeoutError:
            raise asyncio.TimeoutError()
        finally:
            self._redis_waited_answer.pop(waiter.key, None)
        pass

    def set_result_to_redis_queue_request(self, response: Response):
        try:
            waiter = self._redis_waited_answer[response.ri]
        except KeyError:
            self.log.warning(f'awaited request not found {response.ri}')
            return
        self.log.debug(f'return_response - {response}')
        waiter.future = response
        pass


class Waiter:
    def __init__(self, request: Request):
        self._request = request
        self._future = asyncio.Future()
        self._result = []

    @property
    def key(self):
        return self._request.ri

    @property
    def future(self):
        return self._future

    @future.setter
    def future(self, value: Response):
        self._future.set_result(value)

    @property
    def result(self):
        return self._result
