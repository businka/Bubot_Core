import os
from sys import path as syspath

from Bubot.Helpers.ActionDecorator import action
from BubotObj.OcfDevice.subtype.Device.Device import Device


@action
def find_drivers(**kwargs):
    result = {}
    log = kwargs.get('log')
    for path1 in syspath:
        device_dir = os.path.normpath('{}/BubotObj/OcfDevice/subtype'.format(path1))
        if os.path.isdir(device_dir):
            device_list = os.listdir(device_dir)
            for device_name in device_list:
                device_path = os.path.normpath('{0}/{1}/{1}.py'.format(device_dir, device_name))
                if not os.path.isfile(device_path):
                    continue
                try:
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
                    result[device_name] = dict(
                        path=os.path.normpath('{0}/{1}'.format(device_dir, device_name)),
                        # driver=driver
                    )

    return result


def find_schemas(**kwargs):
    result = []
    for path1 in syspath:
        schemas_dir = os.path.normpath(f'{path1}/BubotObj/OcfSchema/schema')
        if os.path.isdir(schemas_dir) and schemas_dir not in result:
            result.append(schemas_dir)

    return result
