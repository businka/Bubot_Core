from Bubot.Helpers.ExtException import ExtException, HandlerNotFoundError
from Bubot.Helpers.Helper import Helper


class BubotHelper:

    @staticmethod
    def get_obj_class(obj_name, **kwargs):
        suffix = kwargs.get('suffix')
        class_name = f'{obj_name}{suffix}' if suffix else obj_name
        full_path = f'BubotObj.{obj_name}.{class_name}.{class_name}'
        try:
            return Helper.get_class(full_path)
        except ExtException as err:
            raise HandlerNotFoundError(detail=f'object {obj_name}', parent=err)

    @staticmethod
    def get_subtype_class(obj_name, subtype, **kwargs):
        suffix = kwargs.get('suffix')
        class_name = f'{subtype}{suffix}' if suffix else subtype
        full_path = f'BubotObj.{obj_name}.subtype.{subtype}.{class_name}.{class_name}'
        try:
            return Helper.get_class(full_path)
        except ExtException as err:
            raise HandlerNotFoundError(detail=f'object {obj_name} subtype {subtype}', parent=err)

    @staticmethod
    def get_extension_class(obj_name, device, **kwargs):
        suffix = kwargs.get('suffix')
        class_name = f'{obj_name}{suffix}' if suffix else obj_name
        full_path = f'BubotObj.{obj_name}.extension.{device}.{class_name}.{class_name}'
        try:
            return Helper.get_class(full_path)
        except ExtException as err:
            raise HandlerNotFoundError(detail=f'object {obj_name} extension {device}', parent=err)
