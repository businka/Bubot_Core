from _datetime import datetime

from aiohttp_session import get_session, new_session

from bubot.core.Obj import Obj
from bubot_helpers.ActionDecorator import async_action
from bubot_helpers.ExtException import KeyNotFound


class Session(Obj):
    name = 'session'

    @property
    def db(self):
        return 'Bubot'

    def init(self):
        self.data = {
            "user_": None,
            "account": None,
            "app_": None,
            "lang": None,
            "begin": datetime.utcnow(),
            "end": None
        }

    @classmethod
    @async_action
    async def init_from_view(cls, view, **kwargs):
        action = kwargs['_action']
        _session = await get_session(view.request)
        if not _session or not _session.identity:  # если авторизация происходит под чужой живой сессией грохаем её
            raise KeyNotFound(detail='session')
        self = cls(view.storage)
        action.add_stat(await self.find_by_id(_session.identity, _form=None))
        return action.set_end(self)

    @classmethod
    @async_action
    async def create_from_request(cls, user, view, *, _action=None, **kwargs):
        old_session = None
        try:
            old_session = _action.add_stat(await cls.init_from_view(view))
            if not old_session.data.get('end'):
                old_user = old_session.data.get('user')
                if old_user:
                    if user.obj_id == old_user['_id']:
                        return old_session
                    else:
                        _action.add_stat(await old_session.close(cause='auth other user'))
        except KeyNotFound:
            pass
        data = kwargs
        data["user"] = user.get_link()
        data["account"] = user.get_default_account()
        data["begin"] = datetime.utcnow()

        if old_session:
            data['_id'] = old_session.data['_id']
            data['date'] = old_session.data['date']
        self = cls(view.storage)
        self.init_by_data(data)
        _action.add_stat(await self.update())
        _session = await new_session(view.request)
        identity = self.get_identity()
        _session.set_new_identity(identity)
        _session['user'] = self.data['user']
        _session['account'] = self.data['account']
        # _session['_id'] = identity
        return self

    @async_action
    async def close(self, uuid=None, **kwargs):
        if uuid:
            await self.find_by_id(uuid)
        self.data['end'] = datetime.utcnow()
        await self.update()

    def get_identity(self):
        return str(self.obj_id)

    @property
    def account_id(self):
        try:
            return self.data['account']
        except:
            return None

    @property
    def user_id(self):
        try:
            return self.data['user_']['_id']
        except:
            return None

    @property
    def app_name(self):
        try:
            return self.data['app']
        except:
            return None