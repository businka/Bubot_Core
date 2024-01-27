import asyncio
import logging
import random
import time
from uuid import uuid4

from bubot_helpers.ExtException import ExtException

from bubot.buject.OcfDevice.subtype.Device.DeviceCore import DeviceCore


class MainLoopMixin(DeviceCore):

    def run(self):
        # try:
        asyncio.get_event_loop()
        self.task = self.loop.create_task(self.main())
        try:
            self.loop.run_until_complete(self.task)
        except KeyboardInterrupt:
            self.log.info("KeyboardInterrupt")
            self.loop.run_until_complete(self.stop())

        if self.log:
            self.log.info("shutdown")
        # except KeyboardInterrupt:
        #     if self.log:
        #         self.log.info("KeyboardInterrupt")
        #     self.task.cancel()
        #     self.loop.run_until_complete(self.task)

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
            di = self.di
            if not di:
                di = str(uuid4())
                self.set_device_id(di)
            self.log = self.get_logger(di)
            self.log.setLevel(getattr(logging, self.get_param('/oic/con', 'logLevel', 'error').upper()))
            self.save_config()

            random_sleep = random.random()
            self.log.info(f"main begin, random sleep {random_sleep}")
            await self.transport_layer.start()
            await asyncio.sleep(random_sleep)

            while True:
                last_run = time.time()
                update_time = self.get_param('/oic/con', 'updateTime', 30)
                self.set_param('/oic/mnt', 'lastRun', last_run)
                status = self.get_param('/oic/mnt', 'currentMachineState', 'pending')
                method = f'on_{status}'
                if not status:
                    break
                if status not in ['cancelled', 'stoppe d']:
                    await self.transport_layer.cloud.connect()

                if not hasattr(self, method):
                    err_msg = f'Unsupported device lifecycle status "{status}"'
                    self.log.error(err_msg)
                    self.set_param('/oic/mnt', 'currentMachineState', 'stopped')
                    self.set_param('/oic/mnt', 'message', err_msg)
                try:
                    await getattr(self, method)()
                    await self.check_changes()
                    current_status = self.get_param('/oic/mnt', 'currentMachineState')
                    sleep_time = 0
                    if current_status == status:  # Если статус не изменился, то следующий статус согласно настройка FPS
                        elapsed_time = time.time() - last_run
                        sleep_time = round(max(0.05, max(update_time - elapsed_time, 0)), 2)
                    await asyncio.sleep(sleep_time)
                except asyncio.CancelledError:
                    if self.get_param('/oic/mnt', 'currentMachineState', 'pending'):
                        self.set_param('/oic/mnt', 'currentMachineState', 'cancelled')
                    else:
                        self.log.info("main cancelled")
                        return
                        # raise asyncio.CancelledError
                except (ExtException, Exception) as err:
                    self.log.error(ExtException(detail=method, parent=err))
                    self.set_param('/oic/mnt', 'currentMachineState', 'stopped')
                    self.set_param('/oic/mnt', 'message', str(err))
                    pass
        except KeyboardInterrupt:
            if self.log:
                self.log.info("KeyboardInterrupt")
            raise
        except ExtException as err:
            self.log.error(str(err))
            raise
        finally:
            await self.transport_layer.stop()
            self.log.info("main end")

    async def on_pending(self):
        self.set_param('/oic/mnt', 'currentMachineState', 'idle', save_config=True)
        self.log.info("pending end")

    async def on_idle(self):
        pass

    async def on_cancelled(self):
        self.log.info("on cancelled")
        self.set_param('/oic/mnt', 'currentMachineState', '')
        raise asyncio.CancelledError()

    async def on_stopped(self):
        self.log.info("on stopped")
        self.set_param('/oic/mnt', 'currentMachineState', 'cancelled')
