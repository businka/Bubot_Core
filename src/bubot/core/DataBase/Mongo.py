from bson.codec_options import CodecOptions
from motor import motor_asyncio
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure

from bubot_helpers.ActionDecorator import async_action
from bubot_helpers.ExtException import ExtException, ExtTimeoutError, KeyNotFound
from bubot_helpers.Helper import get_tzinfo


class Mongo:
    tzinfo = get_tzinfo()

    def __init__(self, **kwargs):
        self.client = kwargs.get('client')

    pass

    @classmethod
    async def connect(cls, device=None, *, url='mongodb://localhost:27017', **kwargs):
        if device:
            url = device.get_param('/oic/con', 'storage_url', 'mongodb://localhost:27017')
        try:
            client = motor_asyncio.AsyncIOMotorClient(
                url,
                serverSelectionTimeoutMS=5000,
                tz_aware=True,
                tzinfo=cls.tzinfo
            )
            res = await client.server_info()
        except ServerSelectionTimeoutError as err:
            raise ExtTimeoutError(message='Mongo connection timeout', parent=err)
        except Exception as err:
            raise ExtException(parent=err, message='Storage not connected')
        return cls(client=client)

    async def close(self):
        self.client.close()

    async def exist_database(self, db):
        db_names = await self.client.list_database_names()
        return db in db_names

    async def exist_table(self, db, name):
        if not await self.exist_database(db):
            return False
        try:
            await self.client[db].validate_collection(name)
            return True
        except OperationFailure:
            return False

    def create_table(self, db, name):
        table = self.client[db][name]

    async def create_index(self, db, name_, keys, **kwargs):
        await self.client[db][name_].create_index(keys, **kwargs)

    async def find_data_base(self, name):
        data_bases = await self.client.list_database_names()
        if name in data_bases:
            return self.client[name]
        return None

    @async_action
    async def update(self, db, table, data, create=True, *, filter=None, pull=None, add_to_set=None, push=None,
                     _action=None, **kwargs):
        if not db:
            raise KeyNotFound(detail='db')
        if not table:
            raise KeyNotFound(detail='table')
        _id = data.get('_id')
        if _id or filter:

            raw_data = {}
            if data:
                raw_data['$set'] = data
            if pull:
                raw_data['$pull'] = pull
            if add_to_set:
                raw_data['$addToSet'] = add_to_set
            if push:
                raw_data['$push'] = push
            if filter:

                res = await self.client[db][table].update_many(
                    filter,
                    raw_data, upsert=create, **kwargs)
            else:
                res = await self.client[db][table].update_one(
                    dict(_id=_id),
                    raw_data, upsert=create, **kwargs)
            if res.upserted_id:
                data['_id'] = res.upserted_id
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

    def set_timezone(self, db, table):
        self.client[db][table].with_options(
            codec_options=CodecOptions(
                tz_aware=False,
                # tzinfo=self.tzinfo
            ))

    async def find_one(self, db, table, filter, **kwargs):
        self.set_timezone(db, table)
        return await self.client[db][table].find_one(filter, **kwargs)

    async def delete_one(self, db, table, filter):
        return await self.client[db][table].delete_one(filter)

    async def delete_many(self, db, table, filter):
        return await self.client[db][table].delete_many(filter)

    async def count(self, db, table, **kwargs):
        return await self.client[db][table].count_documents(
            kwargs.get('filter', {})
        )

    @staticmethod
    def check_db_and_table(db, table, action):
        if not db:
            raise ExtException(message='db not defined', action=action)
        if not table:
            raise ExtException(message='table not defined', action=action)

    async def list(self, db, table, *, filter=None, projection=None, skip=0, limit=1000, order=None, _action=None,
                   **kwargs):
        self.check_db_and_table(db, table, _action)
        self.set_timezone(db, table)
        if filter is not None:
            full_text_search = filter.pop('_search', None)
            if full_text_search:
                filter['$text'] = {'$search': full_text_search}

        cursor = self.client[db][table].find(
            filter=filter,
            projection=projection,
            skip=skip,
            limit=limit
        )
        if order:
            cursor.sort(order)
        result = await cursor.to_list(length=1000)
        await cursor.close()
        return result

    @async_action
    async def get_previous(self, db, table, *, filter=None, index=None, projection=None, skip=0, limit=1000, order=None,
                           _action=None, **kwargs):
        self.check_db_and_table(db, table, _action)
        self.set_timezone(db, table)

        cursor = self.client[db][table].find(
            filter=filter,

        ).sort([(index, -1)]).limit(10)
        result = await cursor.to_list(length=1000)
        await cursor.close()
        return result

    async def pipeline(self, db, table, pipeline, *, projection=None, filter=None, skip=0, sort=None, limit=1000,
                       **kwargs):
        self.set_timezone(db, table)
        self.check_db(db)
        _pipeline = []
        if filter:
            _pipeline.append({'$match': filter})

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

    async def find_one_and_update(self, db, table, filter, data, **kwargs):
        return await self.client[db][table].find_one_and_update(filter, {'$set': data}, **kwargs)

    @classmethod
    def check_db(cls, db):
        if not db:
            raise KeyNotFound(message='Data base not defined')

# #https://www.programmersought.com/article/87956455420/
# def asynchronize(framework, sync_method, doc=None):
#     """Decorate `sync_method` so it accepts a callback or returns a Future.
#
#     The method runs on a thread and calls the callback or resolves
#     the Future when the thread completes.
#
#     :Parameters:
#      - `motor_class`:       Motor class being created, e.g. MotorClient.
#      - `framework`:         An asynchronous framework
#      - `sync_method`:       Unbound method of pymongo Collection, Database,
#                             MongoClient, etc.
#      - `doc`:               Optionally override sync_method's docstring
#     """
#     @functools.wraps(sync_method)
#     def method(self, *args, **kwargs):
#         loop = self.get_io_loop()
#         callback = kwargs.pop('callback', None)
#         future = framework.run_on_executor(loop,
#                                            sync_method,
#                                            self.delegate,
#                                            *args,
#                                            **kwargs)
#
#         return framework.future_or_callback(future, callback, loop)
#
#     # This is for the benefit of motor_extensions.py, which needs this info to
#     # generate documentation with Sphinx.
#     method.is_async_method = True
#     name = sync_method.__name__
#     method.pymongo_method_name = name
#     if doc is not None:
#         method.__doc__ = doc
#
#     return method
