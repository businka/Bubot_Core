import json
import os.path
from sys import path as syspath

from aiohttp.web import json_response, Response

from Bubot.Helpers.ActionDecorator import async_action


class ObjSchemaApi:
    # clear = re.compile('[^a-zA-Z0-9]')
    schemas = dict()

    def __init__(self, response, **kwargs):
        self.response = response
        if not self.schemas:
            self.find_schemas()

    @async_action
    async def api_read(self, view, **kwargs):
        _id = view.request.query.get('id')
        try:
            file_name = self.schemas[_id]
        except KeyError:
            return Response(text=f"Schema not found ({_id})", status=501)

        with open(self.schemas[_id], 'r', encoding='utf-8') as file:
            try:
                data = json.load(file)
                return json_response(data)
            except Exception as e:
                return Response(status=500, text=str(e))

    @classmethod
    def find_schemas(cls, **kwargs):
        '''
        Ищем формы для каждого из предустановленных типов, в общем каталог и каталоге устройства
        :param kwargs:
        :return:
        '''

        for path1 in syspath:
            bubot_dir = f'{path1}/BubotObj/ObjSchema'
            if not os.path.isdir(bubot_dir):
                continue
            obj_list = os.listdir(bubot_dir)
            for obj_name in obj_list:
                schemas_dir = os.path.normpath(f'{bubot_dir}/schema')
                if not os.path.isdir(schemas_dir):
                    continue
                schema_list = os.listdir(schemas_dir)
                for schema_name in schema_list:
                    if schema_name[-5:] != ".json":
                        continue
                    cls.schemas[schema_name[:-5]] = os.path.normpath(f'{schemas_dir}/{schema_name}')
        pass
