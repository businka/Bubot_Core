import json
from os.path import dirname, isfile, join
from uuid import uuid4

from bubot.core.BubotHelper import BubotHelper
from bubot.core.ObjForm import ObjForm
from bubot_helpers.ActionDecorator import async_action
from bubot_helpers.ExtException import KeyNotFound, ExtException
from bubot_helpers.Helper import Helper
from bubot_helpers.Helper import get_tzinfo


class Obj:
    tzinfo = get_tzinfo()
    file = __file__  # должен быть в каждом файле наследники для чтения форм
    extension = False
    is_subtype = None
    name = None
    key_property = '_id'
    uuid_id = True
    _locales = {}
    # описание натуральных ключей объекта
    # массив объектов
    # * key - имя ключа
    # * fields - массив с объектами описывающими получение каждого значения ключа
    #   * path - путь до значения ключа в объекте
    #   * format - правила форматирования значения
    keys_meta = None

    def __init__(self, storage, *, session=None, app_name=None, **kwargs):
        self.data = {}
        self.storage = storage
        self.app_name = app_name
        self.session = session
        self.debug = False

    @property
    def account_id(self):
        return self.session['account'] if self.session else None

    # @property
    # def app_name(self):
    #     return self.session.app_name if self.session else None

    def init(self, **kwargs):
        self.data = dict(
            title=''
        )

    def init_by_data(self, data):
        subtype = data.get('subtype')
        obj_class = self
        if subtype and self.__class__.__name__ != subtype:
            obj_class = self.init_subtype(subtype)
        try:
            obj_class.init()
            if data:
                Helper.update_dict(obj_class.data, data)
            if '_id' not in data:
                obj_class.data['_id'] = str(uuid4())

            if subtype and self.__class__.__name__ != subtype:
                self.data = obj_class.data
            return obj_class
        except Exception as err:
            raise ExtException(parent=err, action=f'{self.__class__.__name__}.init_by_data')

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
        return _action.add_stat(await self.find_one({"_id": _id}, _form=_form, **kwargs))

    @async_action
    async def find_one(self, filter, *, _form="Item", _action=None, **kwargs):
        self.add_projection(_form, kwargs)
        res = await self.storage.find_one(self.db, self.obj_name, filter, **kwargs)
        if res:
            return self.init_by_data(res)
        raise KeyNotFound(message=f'Object not found', detail=f'{self.obj_name}', dump=filter, action=_action)

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
        title = self.data.get('title')
        if add_obj_type:
            result['type'] = self.name
            if self.is_subtype:
                result['subtype'] = self.__class__.__name__

        if title:
            result['title'] = title
        if properties:
            for name in properties:
                value = self.data.get(name)
                if value:
                    result[name] = name

        # for elem in self.data:  # добаляем заголовок на всех языках
        #     if elem[:5] == 'title':
        #         result[elem] = self.data[elem]
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
    async def list(self, *, _form="List", **kwargs):
        self.add_projection(_form, kwargs)
        kwargs = await self.list_set_default_params(**kwargs)
        result = await self.storage.list(self.db, self.obj_name, **kwargs)
        return {'Rows': result}

    async def list_set_default_params(self, **kwargs):
        return kwargs

    async def set_default_params(self, data):
        return data

    async def count(self, **kwargs):
        return await self.storage.count(self.db, self.obj_name, **kwargs)

    @async_action
    async def create(self, data=None, **kwargs):
        return await self.update(data, **kwargs)

    @async_action
    async def before_update(self, data=None, **kwargs):
        if self.keys_meta:
            keys = self.get_keys(data)
            if keys:
                data['keys'] = keys
        pass

    @async_action
    async def update(self, data=None, *, _action=None, **kwargs):
        _data = data if data is not None else self.data
        await self.set_default_params(_data)
        try:
            _data['_id']
        except KeyError:
            if self.uuid_id and not kwargs.get('filter'):
                _data['_id'] = str(uuid4())
        _action.add_stat(await self.before_update(_data, **kwargs))
        res = _action.add_stat(await self.storage.update(self.db, self.obj_name, _data, **kwargs))
        if data is None:
            self.data = _data
        return _data

    @async_action
    async def push(self, field, item, *, _action=None):
        res = await self.storage.push(self.db, self.obj_name, self.obj_id, field, item)
        return res

    @async_action
    async def pull(self, field, item, *, _action=None):
        res = await self.storage.pull(self.db, self.obj_name, self.obj_id, field, item)
        return res

    @async_action
    async def delete_one(self, _id=None, *, filter=None, _action=None):  # todo удаление из починенных таблиц
        _id = self.obj_id if _id is None else _id
        filter = filter if filter else dict(_id=_id)
        await self.storage.delete_one(self.db, self.obj_name, filter)
        pass

    @async_action
    async def delete_many(self, filter, *, _action=None):
        result = await self.storage.delete_many(self.db, self.obj_name, filter)
        return result.raw_result

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

    # @classmethod
    # def get_model(cls):
    #     if cls.model is None:
    #         cls.model = ObjModel.get(cls)
    #     return cls.model

    # @classmethod
    # def get_obj_table(cls):
    #     if cls._obj_table is None:
    #         cls._obj_table = f'{cls._obj_table_prefix}{cls.get_obj_name()}'
    #     return cls._obj_table

    async def find_by_keys(self, keys):
        for key in keys:
            try:
                return await self.find_by_key(**key)
            except KeyError:
                pass
        raise KeyError

    async def find_by_key(self, key, **values):
        res = await self.storage.find_one(self.db, self.obj_name, dict(
            keys=dict(key=key, **values)
        ))
        if res:
            return self.init_by_data(res)
        raise KeyError
        pass

    @property
    def title(self, lang=None):
        return self.data.get('title')

    def __bool__(self):
        return bool(self.data)

    def init_subtype(self, subtype=None):
        _subtype = subtype or self.subtype
        if not _subtype:
            return self
        current_class = self.__class__.__name__
        if current_class == _subtype:
            return self
        try:
            handler = BubotHelper.get_subtype_class(self.__class__.__name__, _subtype)
        except:
            return self
        return handler(self.storage, session=self.session)

    @classmethod
    def get_dir(cls):
        return dirname(cls.file)

    @classmethod
    def read_i18n(cls, lang):
        def i18n_path(cl):
            return join(cl.get_dir(), 'i18n')

        def _read_locale(cl, _locale, _locales):
            locale_path = join(i18n_path(cl), f'{_locale}.json')
            if isfile(locale_path):
                with open(locale_path, "r", encoding='utf-8') as file:
                    try:
                        _data = json.load(file)
                        if isinstance(_data, dict):
                            try:
                                _locales[_locale]
                            except KeyError:
                                _locales[_locale] = {}
                            Helper.update_dict(_locales[_locale], _data)
                        else:
                            raise ExtException(
                                message=f'Build locale',
                                detail=f'{lang} for object {cl.__name__}: Bad format {_data}')
                    except Exception as err:
                        err = ExtException(parent=err)
            return

        try:
            return cls._locales[lang]
        except KeyError:
            pass

        if cls.is_subtype:
            for elem in cls.__bases__:
                if issubclass(elem, Obj):
                    _read_locale(elem, lang, cls._locales)
        _read_locale(cls, lang, cls._locales)
        return cls._locales[lang]

    @classmethod
    def t(cls, value, lang):
        locale = None
        if lang:
            locale = cls.read_i18n(lang)
        if not locale and lang != 'en':
            locale = cls.read_i18n('en')
        return Helper.get_element_in_dict(locale, value, value)

    def data_getter_root_dict(self, name):
        try:
            return self.data[name]
        except KeyError:
            self.data[name] = {}
            return self.data[name]

    def data_getter_root_str(self, name):
        try:
            return self.data[name]
        except KeyError:
            self.data[name] = ''
            return self.data[name]

    def data_getter_root_list(self, name):
        try:
            return self.data[name]
        except KeyError:
            self.data[name] = []
            return self.data[name]

    def data_setter_root(self, name, value):
        self.data[name] = value

    @classmethod
    def get_keys(cls, obj_data, **kwargs):
        if cls.keys_meta is None:
            return None
        keys = []
        for key in cls.keys_meta:
            try:
                key_name = key['key']
                fields = key['fields']
            except KeyError:
                continue
            obj_key = dict(
                key=key_name
            )
            not_null = False
            for index, field in enumerate(fields):
                value = Helper.obj_get_path_value(obj_data, field['path'])

                _value = value
                if value is not None:
                    not_null = True
                    format_value = field.get('format')
                    if format_value:
                        if format_value == 'date':
                            _value = value.strftime('%Y-%m-%d')
                        # elif format_value == 'link':
                        #     try:
                        #         _value = f"{value['ТипИС' + str(connection_index)]}/{value['ИдИС' + str(connection_index)]}"
                        #         title = value.get('Название')
                        #         if title:
                        #             obj_key[f'title{index}'] = title
                        #     except KeyError:
                        #         not_null = False  # todo проверка обязательности ключа
                        #         _value = None
                        else:
                            raise NotImplementedError(f'key format {format_value}')
                    else:
                        _value = str(value)
                obj_key[f'value{index}'] = _value
            if not_null:
                keys.append(obj_key)
        return keys

