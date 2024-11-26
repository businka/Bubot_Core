import json
import os.path
from sys import path as syspath

from aiohttp.web import json_response, Response

from bubot_helpers.ActionDecorator import async_action
from bubot_helpers.ExtException import ExtException, KeyNotFound
from bubot_helpers.JsonSchema4 import JsonSchema4
from bubot.core.BubotHelper import BubotHelper


class ObjSchemaApi:
    # clear = re.compile('[^a-zA-Z0-9]')
    schemas_cache = {}
    loader = None

    def __init__(self, response, **kwargs):
        self.response = response
        if self.loader is None:
            self.loader = ObjSchemaLoader()
            self.loader.find_schemas()

    @async_action
    async def api_read(self, view, **kwargs):
        _id = view.request.query.get('id')
        try:
            schema_data = self.schemas_cache[_id]['data']
            return json_response(schema_data)
        except KeyError:
            pass
        try:
            data = JsonSchema4.load_from_file(_id, cache=self.schemas_cache, loader=self.loader)
            return json_response(data)
        except Exception as e:
            return Response(status=500, text=str(e))


class ObjSchemaLoader:
    def __init__(self):
        self.index = {}
        self.cache = {}

    def load(self, schema_name):
        try:
            path = self.index[schema_name]
        except KeyError:
            raise KeyNotFound(message="Schema not found", detail=schema_name)

        with open(path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            return data

    def find_schemas(self):
        '''
        Ищем формы для каждого из предустановленных типов, в общем каталог и каталоге устройства
        :param kwargs:
        :return:
        '''

        discovered_packages = BubotHelper.find_bubot_packages()
        self.index = {}

        for package_name in discovered_packages:
            package = discovered_packages[package_name]
            obj_schema_dir = os.path.join(package.__path__[0], 'buject', 'ObjSchema', 'schema')
            if not os.path.isdir(obj_schema_dir):
                continue

            schemas_dir = os.path.normpath(obj_schema_dir)

            schema_list = os.listdir(schemas_dir)
            for schema_name in schema_list:
                if schema_name[-5:] != ".json":
                    continue
                self.index[schema_name[:-5]] = os.path.normpath(f'{schemas_dir}/{schema_name}')
