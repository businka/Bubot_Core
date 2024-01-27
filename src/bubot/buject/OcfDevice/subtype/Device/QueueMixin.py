import asyncio

from bubot_helpers.ExtException import ExtException


# _logger = logging.getLogger(__name__)


class QueueMixin:

    async def queue_worker(self, queue, name=''):
        self.log.debug(f'start queue_worker "{name}"')
        while True:
            (future, result) = await queue.get()
            self.log.debug(f'queue worker start. queue "{name}" size {queue.qsize()}')
            try:
                _result = await future
                self.log.debug(f'queue worker complete. {_result}')
                if result and asyncio.isfuture(result):
                    result.set_result(_result)
            except ExtException as err:
                self.log.debug(f'queue worker error. {err}')
                result.set_exception(err)
            except Exception as err:
                err = ExtException(parent=err, action='queue_worker')
                self.log.debug(f'queue worker error. {err}')
                result.set_exception(err)
            finally:
                queue.task_done()

    async def execute_in_queue(self, queue, task, name=''):
        try:
            self.log.debug(f'execute_in_queue {name}')
            result = asyncio.Future()
            queue.put_nowait((task, result))
            return await result
        except ExtException as e:
            raise ExtException(parent=e) from None
        except Exception as e:
            raise ExtException(parent=e, action='QueueMixin.execute_in_queue')
