from BuBot.Core.Obj import Obj


class CatalogObj(Obj):
    name = None
    _obj_table_prefix = 'Cat:'

    def init(self):
        self.data = {
            # "title": "",
            # "keys": []
        }

    async def find_by_keys(self, keys):
        for key in keys:
            try:
                return await self.find_by_key(key['name'], key['value'])
            except KeyError:
                pass
        raise KeyError

    async def find_by_key(self, key_name, key_value):
        res = await self.db.find_one(self.db, self.table, dict(
            keys=dict(name=key_name, value=key_value)
        ))
        if res:
            self.init_by_data(res)
            return res
        raise KeyError
        pass

    @property
    def title(self, lang=None):
        return self.data['title']

    @property
    def obj_type(self):
        return 'Catalog'
