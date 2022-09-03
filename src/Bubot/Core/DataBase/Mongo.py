from urllib.parse import quote_plus, urlparse

from motor import motor_asyncio
from pymongo.errors import ServerSelectionTimeoutError

from Bubot.Helpers.ActionDecorator import async_action
from Bubot.Helpers.ExtException import ExtException, ExtTimeoutError


class Mongo:
    def __init__(self, **kwargs):
        self.client = kwargs.get('client')

    pass

    @classmethod
    async def connect(cls, device=None, *, url='mongodb://localhost:27017', **kwargs):
        if device:
            url = device.get_param('/oic/con', 'storage_url', 'mongodb://localhost:27017')
        try:
            client = motor_asyncio.AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)
            res = await client.server_info()
        except ServerSelectionTimeoutError as err:
            raise ExtTimeoutError(message='Mongo connection timeout', parent=err)
        except Exception as err:
            raise ExtException(parent=err, message='Storage not connected')
        return cls(client=client)

    async def close(self):
        self.client.close()

    async def find_data_base(self, name):
        data_bases = await self.client.list_database_names()
        if name in data_bases:
            return self.client[name]
        return None

    @async_action
    async def update(self, db, table, data, create=True, *, where=None, _action=None, **kwargs):
        if data.get('_id') or where:
            _where = where if where else dict(_id=data['_id'])
            res = await self.client[db][table].update_one(
                _where,
                {'$set': data}, upsert=create, **kwargs)
        else:
            if create:
                res = await self.client[db][table].insert_one(data)
                data['_id'] = res.inserted_id
            else:
                raise KeyError
        return res

    async def push(self, db, table, uid, field, item, **kwargs):
        res = await self.client[db][table].update_one({'_id': uid}, {'$push': {field: item}}, upsert=False)
        return res

    async def pull(self, db, table, uid, field, item, **kwargs):
        res = await self.client[db][table].update_one({'_id': uid}, {'$pull': {field: item}}, upsert=False)
        return res

    async def find_one(self, db, table, where, **kwargs):
        return await self.client[db][table].find_one(where, **kwargs)

    async def delete_one(self, db, table, where):
        return await self.client[db][table].delete_one(where)

    async def delete_many(self, db, table, where):
        return await self.client[db][table].delete_many(where)

    async def count(self, db, table, **kwargs):
        return await self.client[db][table].count_documents(
            kwargs.get('where', {})
        )

    @staticmethod
    def check_db_and_table(db, table, action):
        if not db:
            raise ExtException(message='db not defined', action=action)
        if not table:
            raise ExtException(message='table not defined', action=action)

    async def query(self, db, table, *, where=None, projection=None, skip=0, limit=1000, order=None, _action=None,
                    **kwargs):
        self.check_db_and_table(db, table, _action)
        if where is not None:
            full_text_search = where.pop('_search', None)
            if full_text_search:
                where['$text'] = {'$search': full_text_search}

        cursor = self.client[db][table].find(
            filter=where,
            projection=projection,
            skip=skip,
            limit=limit
        )
        if order:
            cursor.sort(order)
        result = await cursor.to_list(length=1000)
        await cursor.close()
        return result

    async def pipeline(self, db, table, pipeline, *, projection=None, where=None, skip=0, sort=None, limit=1000,
                       **kwargs):
        _pipeline = []
        if where:
            _pipeline.append({'$match': where})

        _pipeline += pipeline

        if projection:
            _pipeline.append({'$project': projection})
        if sort:
            _pipeline.append({'$sort': sort})
        if skip:
            _pipeline.append({'$skip': skip})
        if limit:
            _pipeline.append({'$limit': limit})

        cursor = self.client[db][table].aggregate(_pipeline)
        result = await cursor.to_list(length=limit)
        return result

    async def find_one_and_update(self, db, table, where, data, **kwargs):
        return await self.client[db][table].find_one_and_update(where, {'$set': data}, **kwargs)
