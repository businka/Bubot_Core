from Bubot.Helpers.Action import Action
from Bubot.Helpers.ActionDecorator import async_action
from BubotObj.OcfDevice.subtype.WebServer.ApiHelper import DeviceApi


class CatalogObjApi(DeviceApi):
    handler = None
    extension = False

    @async_action
    async def api_read(self, view, *, _action=None, **kwargs):
        # action = kwargs['_action']
        org = self.handler(view.storage, account_id=view.session.get('account', 'Bubot'))
        _id = view.request.query.get('id')
        result = _action.add_stat(await org.find_by_id(_id))
        return self.response.json_response(result)

    @async_action
    async def api_create(self, view, *, _action: Action = None, **kwargs):
        handler, data = await self.prepare_json_request(view)
        data = _action.add_stat(await self.prepare_create_data(handler, data))
        handler.init_by_data(data)
        await handler.update()
        return self.response.json_response(handler.data)

    @async_action
    async def prepare_create_data(self, handler, data, **kwargs):
        return data

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
    async def api_update(self, view, **kwargs):
        handler, data = await self.prepare_json_request(view)
        handler.init_by_data(data)
        await handler.update()
        return self.response.json_response(handler.data)

    @async_action
    async def api_query(self, view, *, _action: Action = None, **kwargs):
        handler, data = await self.prepare_json_request(view, **kwargs)
        # file_name = '{}/examples/test-query-response.json'.format(os.path.dirname(__file__))
        # with open(file_name, 'r', encoding='utf-8') as file:
        #     data = json.load(file)
        # obj = self.handler(view.storage, account_id=view.session['account'])
        where = self.prepare_query_filter(data)
        data = _action.add_stat(await handler.query(**where))
        data = _action.add_stat(await self.query_convert_result(data))
        return self.response.json_response({"rows": data})

    def prepare_query_filter(self, data):
        page = data.pop('page', None)
        where = {}
        limit = min(self.query_limit, int(data.pop('limit', self.query_limit)))
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
    async def query_convert_result(self, data, *, _action: Action = None):
        return data

    async def prepare_json_request(self, view, **kwargs):
        handler = None
        if self.handler:
            handler = self.handler(view.storage, account_id=view.session.get('account'))
            handler.init()
        data = await view.loads_json_request_data(view)
        return handler, data
