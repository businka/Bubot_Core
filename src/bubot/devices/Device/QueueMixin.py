import asyncio
import logging
from bubot.ExtException import ExtException


# _logger = logging.getLogger(__name__)


class QueueMixin:

    async def queue_worker(self, queue, name=''):
        self.log.debug('queue_worker {}'.format(name))
        while True:
            (future, result) = await queue.get()
            try:
                _result = await future
                result.set_result(_result)
            except ExtException as e:
                result.set_exception(e)
            except Exception as e:
                result.set_exception(ExtException(e, action='queue_worker'))
            finally:
                queue.task_done()

    async def execute_in_queue(self, queue, task, name=''):
        try:
            self.log.debug('execute_in_queue {}'.format(name))
            result = asyncio.Future()
            queue.put_nowait((task, result))
            return await result
        except ExtException as e:
            raise ExtException(e) from None
        except Exception as e:
            raise ExtException(e, action='QueueMixin.execute_in_queue')