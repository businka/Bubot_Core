import asyncio
import time
from datetime import datetime
from bubot.CoapServer import CoapServer
from bubot.devices.Device.DeviceCore import DeviceCore
from bubot.ExtException import ExtException
import logging
import random


class MainLoopMixin(DeviceCore):
    # _logger = logging.getLogger(__name__)

    async def main(self):
        # await self.info("begin main")
        self.coap = CoapServer(self)
        await self.coap.run()

        update_time = self.get_param('/oic/con', 'updateTime', 10)
        await asyncio.sleep(random.random())

        while True:
            last_run = time.time()
            self.set_param('/oic/mnt', 'lastRun', last_run)
            status = self.get_param('/oic/mnt', 'currentMachineState', 'pending')
            try:
                method = 'on_{0}'.format(status)
                await getattr(self, method)()
                await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                if self.get_param('/oic/mnt', 'currentMachineState', 'pending'):
                    self.set_param('/oic/mnt', 'currentMachineState', 'cancelled')
                else:
                    return
                    # raise asyncio.CancelledError
            except ExtException as err:
                self.log.error(err)
                self.set_param('/oic/mnt', 'currentMachineState', 'stopped')
                self.set_param('/oic/mnt', 'message', str(err))
                pass
            except Exception as err:
                self.log.error(ExtException(err))
                self.set_param('/oic/mnt', 'currentMachineState', 'stopped')
                self.set_param('/oic/mnt', 'message', str(err))
                pass

            await self.check_changes()
            elapsed_time = time.time() - last_run
            sleep_time = max(0.01, max(update_time - elapsed_time, 0))
            await asyncio.sleep(sleep_time)
        pass

    async def on_pending(self):
        self.set_param('/oic/mnt', 'currentMachineState', 'idle')

    async def on_idle(self):
        pass

    async def on_cancelled(self):
        self.coap.close()
        self.set_param('/oic/mnt', 'currentMachineState', '')
        raise asyncio.CancelledError()

    async def on_stopped(self):
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            self.set_param('/oic/mnt', 'status', 'cancelled')
