from urllib.parse import quote_plus

from motor import motor_asyncio

from Bubot.Helpers.ActionDecorator import async_action


class Mongo:
    def __init__(self, **kwargs):
        self.client = kwargs.get('client')

    pass

    @classmethod
    def connect(cls, device, **kwargs):
        user = kwargs.get('user')
        if user:
            uri = "mongodb://{user}:{password}@{host}:{port}".format(
                user=quote_plus(user),
                password=quote_plus(kwargs.get('password')),
                host=kwargs.get('host', 'localhost'),
                port=kwargs.get('port', 27017)
            )
        else:
            uri = "mongodb://{host}:{port}".format(
                host=kwargs.get('host', 'localhost'),
                port=kwargs.get('port', 27017)
            )
        client = motor_asyncio.AsyncIOMotorClient(uri)
        return cls(client=client)

    async def find_data_base(self, name):
        data_bases = await self.client.list_database_names()
        if name in data_bases:
            return self.client[name]
        return None

    @async_action
    async def update(self, db, table, data, create=True, **kwargs):
        if data.get('_id'):
            res = await self.client[db][table].update_one(dict(_id=data['_id']), {'$set': data}, upsert=create)
        else:
            if create:
                res = await self.client[db][table].insert_one(data)
                data['_id'] = res.inserted_id
            else:
                raise KeyError
        return res

    @async_action
    async def push(self, db, table, uid, field, item, **kwargs):
        res = await self.client[db][table].update_one({'_id': uid}, {'$push': {field: item}}, upsert=False)
        return res

    @async_action
    async def pull(self, db, table, uid, field, item, **kwargs):
        kwargs.pop('_action')
        res = await self.client[db][table].update_one({'_id': uid}, {'$pull': {field: item}}, upsert=False)
        return res

    @async_action
    async def find_one(self, db, table, _filter, **kwargs):
        kwargs.pop('_action')
        return await self.client[db][table].find_one(_filter, **kwargs)

    async def delete_one(self, db, table, _filter):
        return await self.client[db][table].delete_one(_filter)

    async def delete_many(self, db, table, _filter):
        return await self.client[db][table].delete_many(_filter)

    async def count(self, db, table, **kwargs):
        return await self.client[db][table].count_documents(
            kwargs.get('filter', {})
        )

    @async_action
    async def query(self, db, table, **kwargs):
        cursor = self.client[db][table].find(
            filter=kwargs.get('filter', None),
            projection=kwargs.get('projection', None),
            skip=kwargs.get('skip', 0),
            limit=kwargs.get('limit', 1000)
        )
        sort = kwargs.get('sort')
        if sort:
            cursor.sort(sort)
        result = await cursor.to_list(length=1000)
        await cursor.close()
        return result

    @async_action
    async def pipeline(self, db, table, pipeline, **kwargs):
        projection = kwargs.get('projection')
        filter = kwargs.get('filter')
        skip = kwargs.get('skip', 0)
        sort = kwargs.get('sort')
        limit = kwargs.get('limit', 1000)
        _pipeline = []
        _pipeline += pipeline
        if filter:
            _pipeline.append({'$match': filter})
        if projection:
            _pipeline.append({'$project': projection})
        if sort:
            _pipeline.append({'$sort': sort})
        if skip:
            _pipeline.append({'$skip': skip})
        if limit:
            _pipeline.append({'$limit': limit})

        cursor = self.client[db][table].aggregate(_pipeline)
        result = await cursor.to_list(length=1000)
        return result

    async def find_one_and_update(self, db, table, filter, data):
        return await self.client[db][table].find_one_and_update(filter, data)
