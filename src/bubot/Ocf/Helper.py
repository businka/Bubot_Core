import os
from typing import TYPE_CHECKING
from uuid import uuid4

from bubot.buject.OcfDevice.subtype.Device.Device import Device
from bubot.core.BubotHelper import BubotHelper
from bubot_helpers.ActionDecorator import action

if TYPE_CHECKING:
    from bubot.core.DeviceLink import DeviceLink


@action
def find_drivers(**kwargs):
    result = {}
    log = kwargs.get('log')
    buject_index = BubotHelper.init_buject_index()
    for buject in buject_index:
        obj_name, subtype = buject.split('/')
        if not subtype or obj_name != 'OcfDevice':
            continue
        device_name = subtype

        try:
            # print(f'{device_name} {device_path}')
            driver = Device.init_from_config(class_name=device_name, save_config=False)
        except Exception as err:
            if log:
                log.error(f'Init from config {device_name}: {err}')
            continue
        if driver.template:
            continue
        add_driver = True
        filter_rt = kwargs.get('rt')
        if filter_rt:
            try:
                find = False
                for href in driver.data:
                    rt = driver.data[href].get('rt')
                    if filter_rt in rt:
                        find = True
                        break
                if not find:
                    add_driver = False
            except Exception as e:
                add_driver = False
        if add_driver:
            result[device_name] = buject_index[buject]

    return result


def find_schemas(**kwargs):
    packages = BubotHelper.find_bubot_packages()
    result = []
    for package_name in packages:
        package = packages[package_name]
        schemas_dir = os.path.normpath(f'{package.__path__[0]}/buject/OcfSchema/schema')
        if os.path.isdir(schemas_dir) and schemas_dir not in result:
            result.append(schemas_dir)

    return result
