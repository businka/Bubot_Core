from bubot.core.Obj import Obj
from bubot_helpers.ActionDecorator import async_action
from bubot_helpers.ExtException import ExtException, AccessDenied, KeyNotFound, Unauthorized
from bubot_helpers.Helper import ArrayHelper


class User(Obj):
    name = 'user'
    file = __file__

    @property
    def db(self):
        return 'Bubot'

    @classmethod
    async def find_by_cert(cls, storage, cert, create=False):
        data = cert.get_user_data_from_cert()
        self = cls(storage)
        try:
            data = await self.find_by_keys(data['keys'])
            self.init_by_data(data)
        except KeyError:
            if create:
                self.init_by_data(data)
                await self.update()
            else:
                raise KeyError
        return self

    @async_action
    async def add_auth(self, data, *, _action=None, **kwargs):
        session = kwargs.get('session', {})
        user_id = session.get('user')
        try:
            _action.add_stat(await self.find_user_by_auth(data['type'], data['id']))
            raise ExtException(message='Такой пользователь уже зарегистрирован')
        except Unauthorized:
            pass
        if user_id:
            try:
                _action.add_stat(await self.find_by_id(user_id, projection={'_id': 1, 'auth': 1}))
                _action.add_stat(await self.push('auth', data))
            except KeyError:
                session['user'] = None
        else:
            self.data = {
                'title': data.pop('title', data['id']),
                'auth': [data]
            }
            res = _action.add_stat(await self.update())
            return res

    @async_action
    async def del_auth(self, auth_type, auth_id, *, _action=None, **kwargs):
        try:
            res = _action.add_stat(await self.update(
                {},
                where={"_id": self.obj_id},
                pull={"auth": {"type": auth_type, "id": auth_id}}
            ))
            return res
        except Unauthorized:
            pass

    @async_action
    async def update_auth(self, auth_data, *, _action=None, **kwargs):
        try:
            _user = User(self.storage)
            auth_type = auth_data['type']
            auth_id = auth_data['id']
            try:
                _user = User(self.storage)
                res = _action.add_stat(await _user.find_user_by_auth(auth_type, auth_id))
                _action.add_stat(await _user.del_auth(auth_type, auth_id))
            except Unauthorized:
                pass
            _action.add_stat(await self.push('auth', auth_data))
        except Exception as err:
            raise ExtException(parent=err)

        # res = _action.add_stat(await self.update({
        #     '_id': self.obj_id,
        #     'auth.$[auth]': auth_data,
        # },
        #     array_filters=[
        #     {'auth.type': auth_data['type']}
        # ]))

    @async_action
    async def find_user_by_auth(self, _type, _id, *, _action=None, **kwargs):
        # self.add_projection(kwargs)
        # kwargs['projection']['auth'] = True
        res = _action.add_stat(await self.list(
            where={
                'auth.type': _type,
                'auth.id': _id,
            },
            _form=None,
            limit=1
        ))
        if not res['rows']:
            raise Unauthorized()
        user_data = res['rows'][0]
        i = ArrayHelper.find_one(user_data['auth'], {'type': _type, 'id': _id})
        if i < 0:
            raise Unauthorized()
        auth = user_data.pop('auth')
        self.init_by_data(user_data)
        return auth[i]

    def get_default_account(self):
        accounts = self.data.get('account', [])
        if not accounts:
            return 'Bubot'

        _account = self.data.get('last_account')
        if _account is None:
            _account = accounts[0]
        return _account

    @classmethod
    @async_action
    async def check_right(cls, **kwargs):
        # Оболочка проверяет, являетесь ли вы владельцем объекта, к которому вы хотите получить доступ.
        # Если вы являетесь этим владельцем, вы получаете разрешения и оболочка прекращает проверку.
        # Если вы не являетесь владельцем объекта, оболочка проверит, являетесь ли вы участником группы,
        # у которой есть разрешения на этот файл. Если вы являетесь участником этой группы, вы получаете
        # доступ к объекту с разрешениями, которые для группы установлены, и оболочка прекратит проверку.
        # Если вы не являетесь ни пользователем, ни владельцем группы, вы получаете права других
        # пользователей (Other).
        # нет             0000 0
        # чтение          0001 1
        # запись          0010 2
        # чтение и запись 0011 3
        # выполнение

        action = kwargs['_action']
        try:
            storage = kwargs['storage']
            user_ref = kwargs['user']
            account_id = kwargs['account']
            object_name = kwargs['object']
            level = kwargs['level']
            params = kwargs.get('params', {})
        except KeyError as key:
            raise KeyNotFound(detail=str(key))
        try:
            user = cls(storage, account_id=account_id)
            action.add_stat(await user.find_by_id(user_ref['_id'], _form='AccessRight'))
            rights = user.data.get('right')
        except Exception as err:
            raise AccessDenied(parent=err)
        if not rights:
            raise AccessDenied(detail='Empty access list')
        try:
            _level = rights[object_name]
        except Exception:
            raise AccessDenied(detail=object_name)
        if _level < level:
            raise AccessDenied(detail=object_name)
        pass
