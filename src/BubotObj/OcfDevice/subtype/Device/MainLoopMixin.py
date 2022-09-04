import asyncio
import random
import time
import logging
from uuid import uuid4

from Bubot.Helpers.ExtException import ExtException
from BubotObj.OcfDevice.subtype.Device.DeviceCore import DeviceCore


class MainLoopMixin(DeviceCore):
    # _logger = logging.getLogger(__name__)

    def run(self):
        self.loop = asyncio.get_event_loop()
        self.task = self.loop.create_task(self.main())
        self.loop.run_until_complete(self.task)
        if self.log:
            self.log.info("shutdown")

    async def stop(self):
        try:
            if self.task:
                self.task.cancel()
                await self.task
        except asyncio.CancelledError:
            pass

    async def main(self):
        try:
            self.change_provisioning_state()
            di = self.get_device_id()
            if not di:
                di = str(uuid4())
                self.set_device_id(di)
            self.log = logging.getLogger('{0}:{1}'.format(self.__class__.__name__, di[-5:]))
            self.log.setLevel(getattr(logging, self.get_param('/oic/con', 'logLevel', 'error').upper()))

            self.log.info("begin main")
            await self.transport_layer.start()
            await asyncio.sleep(random.random())

            while True:
                last_run = time.time()
                update_time = self.get_param('/oic/con', 'updateTime', 30)
                self.set_param('/oic/mnt', 'lastRun', last_run)
                status = self.get_param('/oic/mnt', 'currentMachineState', 'pending')
                method = f'on_{status}'
                try:
                    await getattr(self, method)()
                    await self.check_changes()
                    current_status = self.get_param('/oic/mnt', 'currentMachineState')
                    if current_status == status:  # Если статус не изменился, то следующий статус согласно настройка FPS
                        elapsed_time = time.time() - last_run
                        sleep_time = max(0.01, max(update_time - elapsed_time, 0))
                        await asyncio.sleep(sleep_time)
                except asyncio.CancelledError:
                    if self.get_param('/oic/mnt', 'currentMachineState', 'pending'):
                        self.set_param('/oic/mnt', 'currentMachineState', 'cancelled')
                    else:
                        self.log.info("cancelled main")
                        return
                        # raise asyncio.CancelledError
                except (ExtException, Exception) as err:
                    self.log.error(ExtException(detail=method, parent=err))
                    self.set_param('/oic/mnt', 'currentMachineState', 'stopped')
                    self.set_param('/oic/mnt', 'message', str(err))
                    pass

        except ExtException as err:
            self.log.error(str(err))
            raise
        finally:
            await self.transport_layer.stop()
            self.log.info("end main")

    async def on_pending(self):
        self.log.info("on_pending")
        self.set_param('/oic/mnt', 'currentMachineState', 'idle', save_config=True)

    async def on_idle(self):
        pass

    async def on_cancelled(self):
        self.log.info("on_cancelled")
        self.set_param('/oic/mnt', 'currentMachineState', '')
        raise asyncio.CancelledError()

    async def on_stopped(self):
        self.log.info("on_stopped")
        self.set_param('/oic/mnt', 'currentMachineState', 'cancelled')
