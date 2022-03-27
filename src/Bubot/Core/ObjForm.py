from json import load
from os.path import dirname, normpath, isfile


class ObjForm:
    def __init__(self, **kwargs):
        self.data = kwargs.get('data')

    @classmethod
    def get_form(cls, obj_handler, form_name):
        form_path = normpath(f'{dirname(obj_handler.file)}/forms/{form_name}.form.json')
        if not isfile(form_path):
            if not obj_handler.extension:
                return None
            for elem in obj_handler.__bases__:
                if hasattr(elem, 'get_form'):
                    return cls.get_form(elem, form_name)

        with open(form_path, 'r', encoding='utf-8') as file:
            return cls(data=load(file))

    def get_projection(self, default):
        if 'projection' not in self.data:
            return default
        projection = self.data['projection']
        if not projection:
            return projection
        res = {}
        for elem in projection:
            if projection[elem]:
                res[elem] = True
        return res

    @classmethod
    def add_projection(cls, obj_handler, form_name, obj):
        self = cls.get_form(obj_handler.__class__, form_name)
        if self:
            obj['projection'] = self.get_projection({obj_handler.key_property: 1})
        else:
            obj['projection'] = {obj_handler.key_property: 1}
