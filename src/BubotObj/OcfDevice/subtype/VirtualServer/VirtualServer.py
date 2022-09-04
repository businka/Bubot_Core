import asyncio
import concurrent.futures
import logging
import logging.handlers
import multiprocessing
import queue

from Bubot.Core.DeviceLink import ResourceLink
from Bubot.Helpers.ExtException import KeyNotFound
from Bubot.Helpers.Helper import ArrayHelper
from BubotObj.OcfDevice.subtype.Device.Device import Device
from BubotObj.OcfDevice.subtype.VirtualServer import __version__ as device_version
from Bubot.Helpers.ExtException import ExtException

# _logger = multiprocessing.get_logger()


class VirtualServer(Device):
    version = device_version
    template = False
    file = __file__
    run_dev = ('/oic/con', 'running_devices')

    def __init__(self, **kwargs):
        self._running_devices = {}
        self.loop = None
        self.task = None
        self.task_logger = None
        self.queue = None
        Device.__init__(self, **kwargs)

    async def logger(self):
        def _get(_queue):
            return _queue.get()

        executor = concurrent.futures.ThreadPoolExecutor()
        while True:
            try:
                record = await self.loop.run_in_executor(executor, _get, self.queue)
                if record is None:  # We send this as a sentinel to tell the listener to quit.
                    break
                logger = logging.getLogger(record.name)
                logger.handle(record)  # No level or filter logic applied - just do it!
            except queue.Empty:
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                return
            except Exception as e:
                import sys, traceback
                print('Whoops! Problem:', file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
            executor.shutdown()

    async def on_pending(self):
        if multiprocessing.current_process().name == 'MainProcess':
            self.queue = multiprocessing.Queue(-1)
            self.task_logger = self.loop.create_task(self.logger())

        links = self.get_param('/oic/con', 'running_devices')
        if links:
            for link in links:
                try:
                    device = await self.action_run_device(link)
                    if device:
                        link['n'] = device.get_device_name()
                except Exception as err:
                    raise ExtException(message='Not run device', detail=f'{link.get("n")} - {str(err)}', parent=err)
        await super().on_pending()
        self.save_config()

    async def on_cancelled(self):
        if self.queue:
            self.queue.close()
        try:
            if self.task_logger:
                self.task_logger.cancel()
                await self.task_logger
        except asyncio.CancelledError:
            pass

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
        await super().on_stopped()

    async def on_update_oic_con(self, message):
        # if 'running_devices' in result:
        #     new_links =

        # async def post_devices(self, message):

        links = self.get_param(*self.run_dev)
        new_links = message.cn.pop('running_devices', [])

        # index_current_link = Helper.index_list(current_link, 'di')
        index_list = ArrayHelper.index_list(new_links, 'di')
        changed_links = False
        for link in reversed(links):
            if link['di'] not in index_list:
                changed_links = True
                await self.action_del_device(link['di'])

        index_list = ArrayHelper.index_list(links, 'di')
        for link in reversed(new_links):
            if 'di' not in link or link['di'] not in index_list:
                changed_links = True
                await self.action_add_device(link)
        # изменять существующие записи нельзя
        self.set_param(*self.run_dev, links)
        result = self.update_param(message.to.href, None, message.cn)
        if changed_links:
            result['running_devices'] = self.get_param(*self.run_dev)
        return result

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
        raise Exception('OcfDevice not found')

    async def action_run_device(self, link):
        di = link.get('di')
        try:
            class_name = link['dmno']
        except KeyError:
            raise KeyNotFound(detail='dmno', action='action_run_device') from None
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
            return None

        else:
            device = Device.init_from_file(
                class_name=class_name,
                di=link.get('di'),
                path=self.path,
                loop=self.loop,
                log=self.log
            )
            link['di'] = device.get_device_id()
            task = self.loop.create_task(device.main())
            device.task = task
            self._running_devices[link['di']] = device
            return device

    async def action_stop_device(self, di):
        try:
            self._running_devices[di].task.cancel()
            await self._running_devices[di].task
        except asyncio.CancelledError:
            pass

    @staticmethod
    def device_process(class_name, di, queue, kwargs):
        h = logging.handlers.QueueHandler(queue)  # Just the one handler needed
        kwargs['loop'] = asyncio.new_event_loop()
        root = logging.getLogger()
        root.handlers = []
        root.addHandler(h)
        device = Device.init_from_file(
            class_name=class_name,
            di=di,
            **kwargs
        )
        device.run()
