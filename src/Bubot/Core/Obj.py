from uuid import uuid4

from Bubot.Core.BubotHelper import BubotHelper
from Bubot.Core.ObjForm import ObjForm
from Bubot.Core.ObjModel import ObjModel
from Bubot.Helpers.ActionDecorator import async_action
from Bubot.Helpers.ExtException import KeyNotFound
from Bubot.Helpers.Helper import Helper


class Obj:
    file = __file__  # должен быть в каждом файле наследники для чтения форм
    extension = False
    name = None
    key_property = '_id'
    uuid_id = True

    def __init__(self, storage, *, account_id=None, lang=None, data=None, **kwargs):
        self.storage = storage
        self.account_id = account_id
        self.lang = lang
        data = data
        if data:
            self.init_by_data(data)
        else:
            self.data = {}
        self.debug = False

    def init(self):
        self.data = dict(
            title=''
        )

    def init_by_data(self, data):
        self.init()
        if data:
            Helper.update_dict(self.data, data)
        if '_id' not in data:
            self.data['_id'] = str(uuid4())

    # @classmethod
    # @async_action
    # async def init_by_ref(cls, store, obj_link, **kwargs):
    #     try:
    #         _ref = obj_link['_ref']
    #     except KeyError as err:
    #         raise KeyNotFound(detail=err)
    #     obj_name = _ref.collection
    #     _id = _ref.id
    #     obj_class = BubotHelper.get_obj_class(obj_name)
    #     return obj_class(store, **kwargs)

    # @async_action
    # async def find_by_link(self, obj_link, **kwargs):
    #     return await self.find_by_id(obj_link['_ref'].id, **kwargs)

    @async_action
    async def find_by_id(self, _id, *, _form="Item", _action=None, **kwargs):
        if not _id:
            raise KeyNotFound(message=f'Object id not defined', detail=f'{self.obj_name}')
        res = _action.add_stat(await self.find_one({"_id": _id}, _form=_form, **kwargs))
        if res:
            self.init_by_data(res)
            return res
        raise KeyNotFound(message=f'Object not found', detail=f'{self.obj_name} (id: {_id})')

    @async_action
    async def find_one(self, where, *, _form="Item", _action=None, **kwargs):
        self.add_projection(_form, kwargs)
        res = await self.storage.find_one(self.db, self.obj_name, where, **kwargs)
        if res:
            self.init_by_data(res)
            return res
        raise KeyNotFound(message=f'Object not found', detail=f'{self.obj_name}', dump=where, action=_action)

    def get_link(self, *, properties=None, add_obj_type=False):
        '''
        :param add_obj_type: признак необходимости добавлять тип объекта
        :param properties: список свойств объекта которые нужно включить в ссылку
        :return: объект ссылки
        '''

        result = {
            # "_ref": DBRef(self.obj_name, self.obj_id)
            "_id": self.obj_id
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
        return self.data.get('_id')

    @obj_id.setter
    def obj_id(self, value):
        self.data['_id'] = value

    @property
    def subtype(self):
        return self.data.get('subtype')

    @property
    def db(self):
        return self.account_id

    @async_action
    async def query(self, *, _form="List", **kwargs):
        self.add_projection(_form, kwargs)
        kwargs = await self.query_set_default_params(**kwargs)
        return await self.storage.query(self.db, self.obj_name, **kwargs)

    async def query_set_default_params(self, **kwargs):
        return kwargs

    async def set_default_params(self, data):
        return data

    async def count(self, **kwargs):
        return await self.storage.count(self.db, self.obj_name, **kwargs)

    @async_action
    async def update(self, data=None, **kwargs):
        data = data if data else self.data
        await self.set_default_params(data)
        try:
            data['_id']
        except KeyError:
            if self.uuid_id and not kwargs.get('where'):
                data['_id'] = str(uuid4())
        return await self.storage.update(self.db, self.obj_name, data, **kwargs)

    @async_action
    async def push(self, field, item, *, _action=None):
        res = await self.storage.push(self.db, self.obj_name, self.obj_id, field, item)
        return res

    @async_action
    async def pull(self, field, item, *, _action=None):
        res = await self.storage.pull(self.db, self.obj_name, self.obj_id, field, item)
        return res

    @async_action
    async def delete_one(self, _id=None, *, where=None, _action=None):  # todo удаление из починенных таблиц
        _id = self.obj_id if _id is None else _id
        where = where if where else dict(_id=_id)
        await self.storage.delete_one(self.db, self.obj_name, where)
        pass

    @async_action
    async def delete_many(self, where, *, _action=None):
        await self.storage.delete_many(self.db, self.obj_name, where)
        pass

    async def create(self, data=None):
        data = data if data else self.data
        await self.set_default_params(data)
        await self.storage.createupdate(self.db, self.obj_name, self.data)
        pass

    @classmethod
    def get_form(cls, form_name):
        return ObjForm.get_form(cls, form_name)

    def add_projection(self, form_id, dest_obj):
        if form_id:
            return ObjForm.add_projection(self, form_id, dest_obj)

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
        res = await self.storage.find_one(self.db, self.obj_name, dict(
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

    def __bool__(self):
        return bool(self.data)

    def init_subtype(self, subtype=None):
        if subtype is None:
            subtype = self.subtype
        if not subtype:
            return self
        current_class = self.__class__.__name__
        if current_class == subtype:
            return self
        handler = BubotHelper.get_subtype_class(self.__class__.__name__, subtype)
        return handler(self.storage, account_id=self.account_id, lang=self.lang, data=self.data)
