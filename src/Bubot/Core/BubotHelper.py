import os

from bubot_helpers.ExtException import ExtException, HandlerNotFoundError
from bubot_helpers.Helper import Helper


class BubotHelper:
    buject_index = None

    @classmethod
    def get_package_name(cls, obj_name, subtype=''):
        cls.init_buject_index()
        key = f'{obj_name}/{subtype}'
        try:
            return cls.buject_index[key][0][0]
        except (KeyError, TypeError):
            raise HandlerNotFoundError(detail=f'object {key}')

    @classmethod
    def get_buject_class(cls, package_name, obj_name, subtype=None, *, suffix=None):
        if subtype:
            class_name = f'{subtype}{suffix}' if suffix else subtype
            folder_name = f'{obj_name}.subtype.{subtype}'
        else:
            class_name = f'{obj_name}{suffix}' if suffix else obj_name
            folder_name = obj_name
        full_path = f'{package_name}.buject.{folder_name}.{class_name}.{class_name}'
        return Helper.get_class(full_path)

    @classmethod
    def get_obj_class(cls, obj_name, *, suffix=None, **kwargs):
        package_name = cls.get_package_name(obj_name)
        try:
            return cls.get_buject_class(package_name, obj_name, suffix=suffix)
        except ExtException as err:
            raise HandlerNotFoundError(detail=f'package {package_name} object {obj_name}', parent=err)

    @classmethod
    def get_subtype_class(cls, obj_name, subtype, *, suffix=None, **kwargs):
        package_name = cls.get_package_name(obj_name, subtype)
        try:
            return cls.get_buject_class(package_name, obj_name, subtype, suffix=suffix)
        except ExtException as err:
            raise HandlerNotFoundError(detail=f'package {package_name} object {obj_name} subtype {subtype}', parent=err)

    @classmethod
    def get_extension_class(cls, device, obj_name, subtype=None, *, suffix=None, **kwargs):
        package_name = cls.get_package_name('OcfDevice', device)
        try:
            return cls.get_buject_class(package_name, obj_name, subtype, suffix=suffix)
        except ExtException as err:
            raise HandlerNotFoundError(detail=f'object {obj_name} extension {subtype}', parent=err)

    @staticmethod
    def find_bubot_packages():
        import importlib
        import pkgutil

        discovered_packages = {
            name: importlib.import_module(name)
            for finder, name, ispkg
            in pkgutil.iter_modules()
            if name.startswith('bubot_')
        }
        discovered_packages['bubot'] = importlib.import_module('bubot')
        return discovered_packages

    @classmethod
    def init_buject_index(cls):
        discovered_packages = cls.find_bubot_packages()
        cls.buject_index = {}

        for package_name in discovered_packages:
            plugin = discovered_packages[package_name]
            cls.find_buject_in_package(plugin, cls.buject_index)
        return cls.buject_index

    @staticmethod
    def find_buject_in_package(package, index: dict):
        def _add(_key):
            if _key in index:
                index[_key].append((package.__name__, package.__path__[0]))
            else:
                index[_key] = [(package.__name__, package.__path__[0])]

        buject_dir = os.path.join(package.__path__[0], 'buject')
        if not os.path.isdir(buject_dir):
            return
        bujects = os.listdir(buject_dir)
        for buject_name in bujects:
            if not os.path.isdir(os.path.join(buject_dir, buject_name)):
                continue
            # if os.path.isfile(os.path.join(buject_dir, buject_name, f'{buject_name}.py')):
            if os.path.isfile(os.path.join(buject_dir, buject_name, '__init__.py')):
                    _add(f'{buject_name}/')
            subtype_dir = os.path.join(buject_dir, buject_name, 'subtype')
            if not os.path.isdir(subtype_dir):
                continue
            subtypes = os.listdir(subtype_dir)
            for subtype_name in subtypes:
                if not os.path.isdir(os.path.join(subtype_dir, subtype_name)):
                    continue
                # if os.path.isfile(os.path.join(subtype_dir, subtype_name, f'{subtype_name}.py')):
                if os.path.isfile(os.path.join(subtype_dir, subtype_name, '__init__.py')):
                    _add(f'{buject_name}/{subtype_name}')
