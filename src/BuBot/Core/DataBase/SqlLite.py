import os
import sqlite3


class SqlLite:
    def __init__(self, **kwargs):
        self.path = kwargs.get('path')
        # self.client = kwargs.get('client')

    pass

    @classmethod
    def connect(cls, device, **kwargs):
        self = cls()
        return self

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

    async def find_one(self, db, table, filter):
        return await self.client[db][table].find_one(filter)

    async def delete_one(self, db, table, filter):
        return await self.client[db][table].delete_one(filter)

    async def delete_many(self, db, table, filter):
        return await self.client[db][table].delete_many(filter)

    async def count(self, db, table, **kwargs):
        return await self.client[db][table].count_documents(
            kwargs.get('filter', {})
        )

    def get_db(self, name, create=True):
        path = os.path.normpath(f'{self.path}/{name}.db')
        if not os.path.isfile(not create and not path):
            raise Exception('db not found')
        return sqlite3.connect(path)

    def get_table(self, name):
        pass

    async def query(self, db, table, **kwargs):
        db = self.get_db(db)
        cursor = self.client[db][table].find(
            filter=kwargs.get('filter', None),
            projection=kwargs.get('projection', None),
            skip=kwargs.get('skip', 0),
            limit=kwargs.get('limit', 0)
        )
        sort = kwargs.get('sort')
        if sort:
            cursor.sort(sort)
        result = await cursor.to_list(length=1000)
        await cursor.close()
        return result

    async def find_one_and_update(self, db, table, filter, data):
        return await self.client[db][table].find_one_and_update(filter, data)
