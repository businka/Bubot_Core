from json import load
from os.path import dirname, normpath, isfile


class ObjModel:
    def __init__(self, **kwargs):
        self.data = kwargs.get('data')

    @classmethod
    def get(cls, obj_handler):
        form_path = normpath(f'{dirname(obj_handler.file)}/{obj_handler.get_name}.model.json')
        if not isfile(form_path):
            return None
        with open(form_path, 'r', encoding='utf-8') as file:
            return cls(data=load(file))

    def get_projections(self):
        fields = self.data.get('fields')
        if not fields:
            return {'_id': 1, 'title': 1}
        res = {}
        for elem in fields:
            if fields[elem]:
                res[elem]: 1
        return res
