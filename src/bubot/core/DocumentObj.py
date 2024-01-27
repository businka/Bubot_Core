from datetime import datetime

from Bubot.Core.Obj import Obj


class DocumentObj(Obj):
    name = None

    def init(self):
        self.data = {
            "title": "",
            "name": "",
            "date": datetime.now(),
            "number": "",
            "keys": []
        }

    # async def find_by_keys(self, keys):
    #     for key in keys:
    #         try:
    #             return await self.find_by_key(key['name'], key['value'])
    #         except KeyError:
    #             pass
    #     raise KeyError
    #
    # async def find_by_key(self, key_name, key_value):
    #     res = await self.db.find_one(self.db, self.name, dict(
    #         keys=dict(name=key_name, value=key_value)
    #     ))
    #     if res:
    #         self.init_by_data(res)
    #         return res
    #     raise KeyError
    #     pass

    @property
    def title(self, lang=None):
        return self.data['title']

    @property
    def obj_type(self):
        return 'Document'
