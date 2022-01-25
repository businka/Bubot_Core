from Bubot.Core.ObjForm import ObjForm
import asyncio
from Bubot.Helpers.Action import async_action
from BubotObj.OcfDevice.subtype.WebServer.ApiHelper import DeviceApi


class CatalogObjApi(DeviceApi):
    handler = None
    extension = False

    @async_action
    async def api_read(self, view, **kwargs):
        # action = kwargs['_action']
        org = self.handler(view.storage, account_id=view.session.get('account', 'Bubot'))
        _id = view.request.query.get('id')
        result = await org.find_by_id(_id)
        return self.response.json_response(result)

    @async_action
    async def api_create(self, view, **kwargs):
        handler, data = await self.prepare_json_request(view)
        handler.init_by_data(data)
        await handler.update()
        await handler.update()
        return self.response.json_response(handler.data)

    @async_action
    async def api_delete(self, view, **kwargs):
        handler, data = await self.prepare_json_request(view)
        await handler.delete_one(data['_id'])
        await handler.update()
        return self.response.json_response(handler.data)

    @async_action
    async def api_update(self, view, **kwargs):
        handler, data = await self.prepare_json_request(view)
        handler.init_by_data(data)
        await handler.update()
        return self.response.json_response(handler.data)

    @async_action
    async def api_query(self, view, **kwargs):
        handler, data = await self.prepare_json_request(view, **kwargs)
        # file_name = '{}/examples/test-query-response.json'.format(os.path.dirname(__file__))
        # with open(file_name, 'r', encoding='utf-8') as file:
        #     data = json.load(file)
        # obj = self.handler(view.storage, account_id=view.session['account'])
        filter = self.prepare_query_filter(data)
        data = await handler.query(**filter)

        # await asyncio.sleep(2)
        return self.response.json_response({"rows": data})

    async def prepare_json_request(self, view, **kwargs):
        handler = self.handler(view.storage, account_id=view.session.get('account'))
        handler.init()
        data = await view.loads_json_request_data(view)
        return handler, data

    def prepare_query_filter(self, data):
        page = data.pop('page', None)
        filter = {}
        limit = min(self.query_limit, int(data.pop('limit', self.query_limit)))
        for key in data:
            try:
                filter[key] = self.filter_fields[key](filter, key, data[key])
            except:
                filter[key] = data[key]
        result = {
            'filter': filter
        }

        if limit:
            result['limit'] = limit
            if page:
                result['skip'] = (int(page) - 1) * result['limit']
        return result
