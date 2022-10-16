from typing import Optional, Type

from Bubot.Core.Obj import Obj
from Bubot.Helpers.Action import Action
from Bubot.Helpers.ActionDecorator import async_action
from BubotObj.OcfDevice.subtype.WebServer.ApiHelper import DeviceApi


class ObjApi(DeviceApi):
    handler: Optional[Type[Obj]] = None
    extension = False

    @async_action
    async def api_read(self, view, *, _action=None, **kwargs):
        handler, data = await self.prepare_json_request(view)
        _id = data.get('id')
        result = _action.add_stat(await handler.find_by_id(_id))
        return self.response.json_response(result)

    # @async_action
    # async def prepare_create_data(self, handler, data, **kwargs):
    #     return data

    @async_action
    async def api_delete(self, view, **kwargs):
        handler, data = await self.prepare_json_request(view)
        await handler.delete_one(data['_id'])
        # await handler.update()
        return self.response.json_response(handler.data)

    @async_action
    async def api_delete_many(self, view, *, _action=None, **kwargs):
        handler, data = await self.prepare_json_request(view)
        _filter = data.get('filter')
        if not _filter:
            _items = data.get('items')
            ids = []
            for item in _items:
                ids.append(item['_id'])
            _filter = {'_id': {'$in': ids}}
        result = _action.add_stat(await handler.delete_many(_filter))
        return self.response.json_response(result)

    @async_action
    async def api_create(self, view, *, _action: Action = None, **kwargs):
        handler, data = await self.prepare_json_request(view)
        handler.init_by_data(data)
        # data = _action.add_stat(await self.prepare_create_data(handler, data))
        # handler.init_by_data(data)
        await handler.create()
        return self.response.json_response(handler.data)

    @async_action
    async def api_update(self, view, **kwargs):
        handler, data = await self.prepare_json_request(view)
        handler.init_by_data(data)
        await handler.update()
        return self.response.json_response(handler.data)

    @async_action
    async def api_list(self, view, *, _action: Action = None, **kwargs):
        handler, data = await self.prepare_json_request(view, **kwargs)
        # file_name = '{}/examples/test-list-response.json'.format(os.path.dirname(__file__))
        # with open(file_name, 'r', encoding='utf-8') as file:
        #     data = json.load(file)
        # obj = self.handler(view.storage, account_id=view.session['account'])
        where = self.prepare_list_filter(data)
        data = _action.add_stat(await handler.list(**where))
        data = _action.add_stat(await self.list_convert_result(data))
        return self.response.json_response({"rows": data})

    def prepare_list_filter(self, data):
        page = data.pop('page', None)
        where = {}
        limit = min(self.list_limit, int(data.pop('limit', self.list_limit)))
        if limit == -1:
            limit = None
        for key in data:
            try:
                where[key] = self.filter_fields[key](where, key, data[key])
            except:
                where[key] = data[key]
        result = {
            'where': where
        }

        if limit:
            result['limit'] = limit
            if page:
                result['skip'] = (int(page) - 1) * result['limit']
        return result

    @async_action
    async def list_convert_result(self, data, *, _action: Action = None):
        return data

    async def prepare_json_request(self, view, **kwargs):
        data = await view.loads_json_request_data(view)

        handler: Optional[Obj] = None
        if self.handler:
            handler = self.handler(view.storage, account_id=view.session.get('account'))
            handler.init()
        return handler, data

    @staticmethod
    def _init_subtype(handler, data):
        try:
            subtype = data['subtype']
        except (KeyError, TypeError):
            subtype = None

        return handler.init_subtype(subtype)
