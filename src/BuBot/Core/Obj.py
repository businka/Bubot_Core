from bson import DBRef

from Bubot.Core.BubotHelper import BubotHelper
from Bubot.Core.ObjForm import ObjForm
from Bubot.Core.ObjModel import ObjModel
from Bubot.Helpers.ActionDecorator import async_action
from Bubot.Helpers.ExtException import KeyNotFound
from Bubot.Helpers.Helper import Helper


class Obj:
    file = __file__
    extension = False
    name = None

    def __init__(self, storage, **kwargs):
        self.storage = storage
        self.account_id = kwargs.get('account_id')
        self.lang = kwargs.get('lang')
        self.form_id = kwargs.get('form')
        self.data = None
        data = kwargs.get('data')
        if data:
            self.init_by_data(data)
        self.debug = False

    def init(self):
        self.data = dict(
            title=''
        )

    def init_by_data(self, data):
        self.init()
        if data:
            Helper.update_dict(self.data, data)

    @classmethod
    @async_action
    async def init_by_ref(cls, store, obj_link, **kwargs):
        try:
            _ref = obj_link['_ref']
        except KeyError as err:
            raise KeyNotFound(detail=err)
        obj_name = _ref.collection
        _id = _ref.id
        obj_class = BubotHelper.get_obj_class(obj_name)
        return obj_class(store, **kwargs)

    @async_action
    async def find_by_link(self, obj_link, **kwargs):
        return await self.find_by_id(obj_link['_ref'].id, **kwargs)

    @async_action
    async def find_by_id(self, _id, **kwargs):
        action = kwargs['_action']
        self.add_projection(kwargs)
        res = action.add_stat(
            await self.storage.find_one(self.db, self.name, dict(_id=_id), **kwargs))
        if res:
            self.init_by_data(res)
            return action.set_end(res)
        raise KeyNotFound()

    def get_link(self, properties=None):
        '''

        :param properties: список свойств объекта которые нужно включить в ссылку
        :return: объект ссылки
        '''

        result = {
            "_ref": DBRef(self.name, self.obj_id)
        }
        for elem in self.data:  # добаляем заголовок на всех языках
            if elem[:5] == 'title':
                result[elem] = self.data[elem]
        return result

    @property
    def obj_name(self):
        return self.name if self.name else self.__class__.__name__

    @property
    def obj_id(self):
        return self.data['_id']

    @obj_id.setter
    def obj_id(self, value):
        self.data['_id'] = value

    @property
    def db(self):
        return self.account_id

    @async_action
    async def query(self, **kwargs):
        return await self.storage.query(self.db, self.name, **kwargs)

    async def count(self, **kwargs):
        return await self.storage.count(self.db, self.name, **kwargs)

    @async_action
    async def update(self, data=None, **kwargs):
        return await self.storage.update(self.db, self.name, data if data else self.data, **kwargs)
        pass

    @async_action
    async def push(self, field, item):
        res = await self.storage.push(self.db, self.name, self.obj_id, field, item)
        return res

    @async_action
    async def pull(self, field, item):
        res = await self.storage.pull(self.db, self.name, self.obj_id, field, item)
        return res

    async def delete_one(self, _id=None, _filter=None):
        # _id = ObjectId(_id) if _id else self.obj_id
        _filter = _filter if _filter else dict(_id=_id)
        await self.storage.delete_one(self.db, self.name, _filter)
        pass

    async def delete_many(self, _filter):
        await self.storage.delete_many(self.db, self.name, _filter)
        pass

    async def create(self, data=None):
        await self.storage.createupdate(self.db, self.name, self.data)
        pass

    @classmethod
    def get_form(cls, form_name):
        return ObjForm.get_form(cls, form_name)

    def add_projection(self, dest_obj):
        if self.form_id:
            return ObjForm.add_projection(self, self.form_id, dest_obj)

    # @classmethod
    # def get_obj_type(cls):
    #     if cls._obj_type is None:
    #         from os import sep
    #         _path = cls.file.split(sep)
    #         if _path[-2] == cls.get_obj_name():
    #             cls._obj_type = _path[-3]
    #     return cls._obj_type
    # 
    # @classmethod
    # def get_obj_name(cls):
    #     return cls.name if cls.name else cls.__name__

    @classmethod
    def get_model(cls):
        if cls.model is None:
            cls.model = ObjModel.get(cls)
        return cls.model

    # @classmethod
    # def get_obj_table(cls):
    #     if cls._obj_table is None:
    #         cls._obj_table = f'{cls._obj_table_prefix}{cls.get_obj_name()}'
    #     return cls._obj_table

    async def find_by_keys(self, keys):
        for key in keys:
            try:
                return await self.find_by_key(key['name'], key['value'])
            except KeyError:
                pass
        raise KeyError

    async def find_by_key(self, key_name, key_value):
        res = await self.storage.find_one(self.db, self.name, dict(
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
