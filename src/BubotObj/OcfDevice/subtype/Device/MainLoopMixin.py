import asyncio
import time

from BubotObj.OcfDevice.subtype.Device.DeviceCore import DeviceCore
from Bubot.Helpers.ExtException import ExtException
import random


class MainLoopMixin(DeviceCore):
    # _logger = logging.getLogger(__name__)

    async def main(self):
        try:
            self.log.info("begin main")
            # self.coap = CoapServer(self)
            await self.transport_layer.start()

            update_time = self.get_param('/oic/con', 'updateTime', 30)
            await asyncio.sleep(random.random())

            while True:
                last_run = time.time()
                self.set_param('/oic/mnt', 'lastRun', last_run)
                status = self.get_param('/oic/mnt', 'currentMachineState', 'pending')
                method = f'on_{status}'
                try:
                    await getattr(self, method)()
                    await asyncio.sleep(0.01)
                except asyncio.CancelledError:
                    if self.get_param('/oic/mnt', 'currentMachineState', 'pending'):
                        self.set_param('/oic/mnt', 'currentMachineState', 'cancelled')
                    else:
                        self.log.info("cancelled main")
                        return
                        # raise asyncio.CancelledError
                except ExtException as err:
                    self.log.error(ExtException(detail=method, parent=err))
                    self.set_param('/oic/mnt', 'currentMachineState', 'stopped')
                    self.set_param('/oic/mnt', 'message', str(err))
                    pass
                except Exception as err:
                    self.log.error(ExtException(detail=method, parent=err))
                    self.set_param('/oic/mnt', 'currentMachineState', 'stopped')
                    self.set_param('/oic/mnt', 'message', str(err))
                    pass

                await self.check_changes()
                elapsed_time = time.time() - last_run
                sleep_time = max(0.01, max(update_time - elapsed_time, 0))
                await asyncio.sleep(sleep_time)
        except ExtException as err:
            self.log.error(f"end main {err}")
            raise
        pass

    async def on_pending(self):
        self.set_param('/oic/mnt', 'currentMachineState', 'idle')

    async def on_idle(self):
        pass

    async def on_cancelled(self):
        await self.coap.close()
        self.set_param('/oic/mnt', 'currentMachineState', '')
        raise asyncio.CancelledError()

    async def on_stopped(self):
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            self.set_param('/oic/mnt', 'status', 'cancelled')
