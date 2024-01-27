from typing import Optional
from urllib.parse import unquote

from bubot.core.Obj import Obj
from bubot.core.ObjApi import ObjApi
from bubot_helpers.Action import Action
from bubot_helpers.ActionDecorator import async_action
from bubot_helpers.ExtException import KeyNotFound, AccessDenied
from .User import User


class UserApi(ObjApi):
    handler: User = User

    @async_action
    async def api_read(self, view, *, _action=None, **kwargs):
        raise NotImplementedError()
        handler, data = await self.prepare_json_request(view)
        _id = data.get('id')
        result = _action.add_stat(await handler.find_by_id(_id))
        return self.response.json_response(result)

    # @async_action
    # async def prepare_create_data(self, handler, data, **kwargs):
    #     return data

    @async_action
    async def api_delete(self, view, **kwargs):
        raise NotImplementedError()
        handler, data = await self.prepare_json_request(view)
        await handler.delete_one(data['_id'])
        # await handler.update()
        return self.response.json_response(handler.data)

    @async_action
    async def api_delete_many(self, view, *, _action=None, **kwargs):
        raise NotImplementedError()

        handler, data = await self.prepare_json_request(view)
        where = data.get('filter')
        if not where:
            _items = data.get('items')
            ids = []
            for item in _items:
                ids.append(item['_id'])
            where = {'_id': {'$in': ids}}
        _action.add_stat(await self._before_delete_many(view, handler, where))
        result = _action.add_stat(await handler.delete_many(where))
        return self.response.json_response(result)

    @async_action
    async def _before_delete_many(self, view, handler, where, *, _action=None, **kwargs):
        pass

    @async_action
    async def api_create(self, view, *, _action: Action = None, **kwargs):
        raise NotImplementedError()

        handler, data = await self.prepare_json_request(view)
        handler.init_by_data(data)
        # data = _action.add_stat(await self.prepare_create_data(handler, data))
        # handler.init_by_data(data)
        await handler.create()
        return self.response.json_response(handler.data)

    @async_action
    async def api_update(self, view, **kwargs):
        raise NotImplementedError()

        handler, data = await self.prepare_json_request(view)
        handler.init_by_data(data)
        await handler.update()
        return self.response.json_response(handler.data)

    @async_action
    async def api_list(self, view, *, _action: Action = None, **kwargs):
        handler, data = await self.prepare_json_request(view, **kwargs)
        await handler.check_right(storage=handler.storage, user=view.session.get('user'), object=handler.name,
                                  level=1, account=handler.db, _action=_action)
        _data = self.prepare_list_filter(view, handler, data)
        data = _action.add_stat(await handler.list(**_data))
        data = _action.add_stat(await self.list_convert_result(data))
        return self.response.json_response({"rows": data})

    def prepare_list_filter(self, view, handler, data):
        where = {}
        _where = data.get('filter', {})
        nav = data.get('nav', {})
        limit = int(nav.get('limit', 25))
        page = int(nav.get('page', 1))

        for elem in self.mandatory_field_in_list_filter:
            try:
                _where[elem]
            except KeyError as err:
                raise KeyNotFound(message='Отсутствует обязательный параметр', detail=str(err))

        if limit == -1:
            limit = None
        for key in _where:
            if key in self.filter_fields:
                self.filter_fields[key](where, key, _where[key])
            else:
                where[key] = _where[key]
        result = {
            'where': where
        }

        if limit:
            result['limit'] = limit
            if page:
                result['skip'] = (int(page) - 1) * limit
        return result

    @async_action
    async def list_convert_result(self, data, *, _action: Action = None):
        return data

    @staticmethod
    def unquote_request_query(query):
        _query = dict(query)
        for elem in _query:
            _query[elem] = unquote(_query[elem])
        return _query

    @staticmethod
    def _init_subtype(handler, data):
        try:
            subtype = data.pop('subtype')
        except (KeyError, TypeError):
            subtype = None
        return handler.init_subtype(subtype)
