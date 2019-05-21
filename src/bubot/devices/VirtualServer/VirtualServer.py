import multiprocessing
from bubot.DeviceLink import ResourceLink
import queue
from bubot.devices.Device.Device import Device
from bubot.devices.VirtualServer import __version__ as device_version
import logging
import logging.handlers
import asyncio
import os
from sys import path as syspath
from bubot.ExtException import ExtException
from bubot.Helper import Helper, ArrayHelper


# _logger = multiprocessing.get_logger()


class VirtualServer(Device):
    version = device_version
    file = __file__
    run_dev = ('/oic/con', 'running_devices')

    def __init__(self, **kwargs):
        self._running_devices = {}
        self.loop = None
        self.task = None
        self.queue = None
        Device.__init__(self, **kwargs)

    def run(self):
        self.log.debug('begin')
        if multiprocessing.current_process().name == 'MainProcess':
            self.queue = multiprocessing.Queue(-1)
            self.task = self.loop.create_task(self.logger())

        self.task = self.loop.create_task(self.main())

        if not self.loop.is_running():
            self.loop.run_forever()
        self.log.debug('end')
        pass

    async def logger(self):
        def _get(_queue):
            return _queue.get()

        while True:
            try:
                record = await self.loop.run_in_executor(None, _get, self.queue)
                if record is None:  # We send this as a sentinel to tell the listener to quit.
                    break
                logger = logging.getLogger(record.name)
                logger.handle(record)  # No level or filter logic applied - just do it!
            except queue.Empty:
                await asyncio.sleep(0.5)
            except Exception as e:
                import sys, traceback
                print('Whoops! Problem:', file=sys.stderr)
                traceback.print_exc(file=sys.stderr)

    async def on_pending(self):
        links = self.get_param('/oic/con', 'running_devices')
        for link in links:
            await self.action_run_device(link)
        await super().on_pending()

    async def on_cancelled(self):
        for di in self._running_devices.keys():
            device = self._running_devices.pop(di)
            self.log.debug('{} begin cancelled'.format(di))
            if isinstance(device, multiprocessing.Process):
                res = await self.find_resource_by_link(ResourceLink.init_from_link(dict(di=di, href='/oic/mnt')))
                await self.request('update', res, dict(currentMachineState='cancelled'))
                for i in range(15):
                    if not device.is_alive():
                        break
                    self.log.debug('wait cancelled {}'.format(di))
                    await asyncio.sleep(i)
            else:
                await device.cancel()

            self.log.debug('{} end cancelled'.format(di))
        await super().on_cancelled()

    async def on_stopped(self):
        pass
        # links = self.get_param(*self.run_dev)
        # for i, link in enumerate(links):
        #     self._running_devices[link['di']][1].cancel()
        # await super().on_stopped()

    async def post_devices(self, message):

        links = self.get_param(*self.run_dev)
        new_links = message.cn.get('running_devices', [])

        # index_current_link = Helper.index_list(current_link, 'di')
        index_list = ArrayHelper.index_list(new_links, 'di')
        for link in reversed(links):
            if link['di'] not in index_list:
                await self.action_del_device(link['di'])

        index_list = ArrayHelper.index_list(links, 'di')
        for link in reversed(new_links):
            if 'di' not in link or link['di'] not in index_list:
                await self.action_add_device(link)
        # изменять существующие записи нельзя
        self.set_param('/oic/con', 'running_devices', links)
        pass

    async def action_add_device(self, link):
        await self.action_run_device(link)
        links = self.get_param(*self.run_dev)
        ArrayHelper.update(links, link, 'di')
        self.set_param(*self.run_dev, links)
        self.save_config()
        pass

    async def action_del_device(self, di):
        links = self.get_param(*self.run_dev)
        for i, link in enumerate(links):
            if link.get('di') == di:
                await self.action_stop_device(di)
                del links[i]
                self.set_param(*self.run_dev, links)
                self.save_config()
                return
        raise Exception('Device not found')

    async def action_run_device(self, link):
        di = link.get('di')
        try:
            class_name = link['dmno']
        except KeyError:
            raise ExtException(7001, detail='dmno', action='action_run_device') from None
        if di and di in self._running_devices:
            raise Exception('device is already running')
        if class_name == 'VirtualServer':
            process = multiprocessing.Process(
                target=self.device_process,
                args=(class_name, di, self.queue, dict(path=self.path)),
                daemon=True
            )
            process.start()
            self._running_devices[link['di']] = process

        else:
            device = Device.init_from_file(
                class_name,
                link.get('di'),
                path=self.path,
                loop=self.loop,
                log=self.log
            )
            link['di'] = device.get_device_id()
            task = self.loop.create_task(device.main())
            device.task = task
            self._running_devices[link['di']] = device

    async def action_stop_device(self, di):
        self._running_devices[di][1].cancel()
        await self._running_devices[di][1]

    def find_drivers(self):
        local_devices = {}
        local_schemas = []
        for path1 in syspath:
            device_dir = '{}/bubot/devices'.format(path1)
            if os.path.isdir(device_dir):
                device_list = os.listdir(device_dir)
                for device_name in device_list:
                    if device_name == 'Device':
                        continue
                    device_path = '{0}/{1}/{1}.py'.format(device_dir, device_name)
                    if os.path.isfile(device_path):
                        local_devices[device_name] = dict(
                            path='{0}/{1}'.format(device_dir, device_name),
                        )
                schemas_dir = '{}/bubot/schemas'.format(path1)
                if os.path.isdir(schemas_dir) and schemas_dir not in local_schemas:
                    local_schemas.append(schemas_dir)

            self.set_param('/oic/mnt', 'drivers', local_devices)
        return local_devices, local_schemas

    @staticmethod
    def device_process(class_name, di, queue, kwargs):
        h = logging.handlers.QueueHandler(queue)  # Just the one handler needed
        kwargs['loop'] = asyncio.new_event_loop()
        root = logging.getLogger()
        root.handlers = []
        root.addHandler(h)
        device = Device.init_from_file(
            class_name,
            di,
            **kwargs
        )
        device.run()
