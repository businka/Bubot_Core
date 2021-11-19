import asyncio
import inspect
from os import path


async def wait_run_device(device):
    device.task = device.loop.create_task(device.main())

    while device.get_param('/oic/mnt', 'currentMachineState') != 'idle':
        try:
            device.task.result()
        except asyncio.InvalidStateError:
            pass
        except Exception as err:
            await asyncio.sleep(0.01)
            raise err
        await asyncio.sleep(0.1)
    return device.task


async def wait_run_device2(device):
    while device.get_param('/oic/mnt', 'currentMachineState') != 'idle':
        try:
            device.task.result()
        except asyncio.InvalidStateError:
            pass
        await asyncio.sleep(0.1)
    return device.task


async def wait_cancelled_device(device, device_task):
    try:
        device.set_param('/oic/mnt', 'currentMachineState', 'cancelled')
        while device.get_param('/oic/mnt', 'currentMachineState') != '':
            try:
                device_task.result()
            except asyncio.InvalidStateError:
                pass
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        pass
    await device_task
    pass


def async_test(f):
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        if inspect.iscoroutinefunction(f):
            future = f(*args)
        else:
            coroutine = asyncio.coroutine(f)
            future = coroutine(*args, **kwargs)
        loop.run_until_complete(future)

    return wrapper


def get_config_path(_file_):
    return '{}/config/'.format(path.dirname(_file_))
