import os
import sqlite3
from bubot_helpers.ExtException import ExtException, ExtTimeoutError, KeyNotFound

class SqlLite:
    def __init__(self, **kwargs):
        self.path = kwargs.get('path')
        self.clients = {}
    pass

    @classmethod
    async def connect(cls, device, **kwargs):
        path = None
        if device:
            default_path = device.path
            path = device.get_param('/oic/con', 'storage_url', default_path)
        return cls(path=path)

    async def find_data_base(self, name):
        data_bases = await self.client.list_database_names()
        if name in data_bases:
            return self.client[name]
        return None

    async def update(self, db, table, data, create=True):
        if data.get('_id'):
            res = await self.client[db][table].update_one(dict(_id=data['_id']), {'$set': data}, upsert=create)
        else:
            if create:
                res = await self.client[db][table].insert_one(data)
                data['_id'] = res.inserted_id
            else:
                raise KeyError
        return res

    async def find_one(self, db, table, filter, *, projection=None):
        res = await self.list(db, table, filter=filter, projection=projection, limit=1, skip=0)
        return res[0] if res else None

    async def delete_one(self, db, table, filter):
        return await self.client[db][table].delete_one(filter)

    async def delete_many(self, db, table, filter):
        return await self.client[db][table].delete_many(filter)

    async def count(self, db, table, **kwargs):
        return await self.client[db][table].count_documents(
            kwargs.get('filter', {})
        )

    def get_db(self, name, create=True):
        try:
            return self.clients[name]
        except KeyError:
            path = os.path.normpath(f'{self.path}/{name}.db')
            if not create and not os.path.isfile(path):
                raise Exception('db not found')
            self.clients[name] = sqlite3.connect(path)
        return self.clients[name]

    def get_table(self, name):
        pass

    async def list(self, db, table, **kwargs):
        def order_to_query(_query, _order):
            if not _order:
                return _query
            res = []
            for elem in _order:
                res.append(f" {elem} {'ASC' if _order[elem] > 0 else 'DESC'}")
            return f"{query} ORDER BY {','.join(res)}"

        try:
            con = self.get_db(db)
            con.row_factory = sqlite3.Row
            cursor = con.cursor()
            projection = kwargs.get('projection', None)
            query = f"SELECT {self._projection_to_query('', projection)} FROM {table}"
            query = self._filter_to_query(query, kwargs.get('filter', None))
            query = order_to_query(query, kwargs.get('', None))
            limit = kwargs.get('limit')
            skip = kwargs.get('skip', 0)
            if limit:
                query += f' LIMIT {limit}'
            if skip:
                query += f' OFFSET {skip}'

            result = []
            for row in cursor.execute(query):
                result.append(dict(row))
            return result
        except Exception as err:
            raise ExtException(parent=err)

    @staticmethod
    def _projection_to_query(_query, _projection):
        if _projection:
            res = []
            for elem in _projection:
                if _projection[elem]:
                    res.append(elem)
            return f"{_query} {','.join(res)}"
        else:
            return f'{_query} *'

    @staticmethod
    def _filter_to_query(_query, _filter):
        if not _filter:
            return _query
        _where = []

        for elem in _filter:
            _where.append(f'{elem} = "{_filter[elem]}"')

        return f"{_query} WHERE {' AND '.join(_where)}"

    async def find_one_and_update(self, db, table, filter, data):
        return await self.client[db][table].find_one_and_update(filter, data)

    async def close(self):
        return