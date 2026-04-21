import hashlib
import os
from base64 import b64encode, b64decode
import datetime
from bubot.core.ObjApi import ObjApi
from bubot_helpers.ActionDecorator import async_action
from bubot_helpers.ExtException import KeyNotFound, Unauthorized, AccessDenied
from bubot.buject.Session.Session import Session
from bubot.buject.User.User import User
from aiohttp import web


class UserApi(ObjApi):
    name = "User"
    handler = User
    file = __file__
    extension = True

    @async_action
    async def public_api_sign_in_by_password(self, view, *, _action=None, **kwargs):
        current_datetime = datetime.datetime.now(datetime.timezone.utc)
        try:
            login = view.data['login']
            password = view.data['password']
        except KeyError as err:
            raise KeyNotFound(detail=err)
        user = User(view.storage, lang=view.lang, form='CurrentUser')
        try:
            _auth = _action.add_stat(await user.find_user_by_auth('password', login))
        except Unauthorized:
            raise AccessDenied(message='Bad login or password')
        _auth['bad_attempts'] = _auth.get('bad_attempts', 0)
        if _auth['bad_attempts']:
            next_attempt: datetime = _auth.get('next_attempt')
            if next_attempt and current_datetime < next_attempt:
                time_to_text_attempt = str(next_attempt - current_datetime).split('.')
                raise AccessDenied(message='Bad last login or password', detail=f"{time_to_text_attempt[0]}")
        bad_password = Unauthorized(message='Bad login or password')
        _password = b64decode(_auth['password'])
        salt = _password[:32]
        if _auth['id'] != login or _password != self.generate_password_hash(salt, password):
            _auth['bad_attempts'] += 1
            _auth['next_attempt'] = current_datetime + datetime.timedelta(seconds=30 * (_auth['bad_attempts'] - 1))
            _action.add_stat(await user.update_auth(_auth))
            raise bad_password
        # _session = kwargs['session']
        _auth['bad_attempts'] = 0
        _auth['next_attempt'] = current_datetime
        _action.add_stat(await user.update_auth(_auth))
        session = _action.add_stat(await Session.create_from_request(user, view))
        _action.set_end(self.response.json_response({
            'session': str(session.obj_id),
            'user': user.data
        }))
        return _action

    @async_action
    async def public_api_sign_up_by_password(self, view, **kwargs):
        action = kwargs['_action']
        try:
            login = view.data['login']
            password = view.data['password']
        except KeyError as err:
            raise KeyNotFound(detail=err)

        salt = os.urandom(32)
        password = b64encode(self.generate_password_hash(salt, password)).decode()

        user = User(view.storage, lang=view.lang, form='CurrentUser')
        res = action.add_stat(await user.add_auth({
            'type': 'password',
            'id': login,
            'password': password
        }, **kwargs))
        # if res:
        # if str(b64encode(password)) == res.get('password'):
        session = action.add_stat(await Session.create_from_request(user, view))
        return self.response.json_response({'session': str(session.obj_id)})

    @staticmethod
    def generate_password_hash(salt, password):
        return salt + hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)

    @async_action
    async def public_api_read_session_info(self, view, **kwargs):
        action = kwargs['_action']
        try:
            user_link = view.session.get('user_')
            if not user_link:
                return web.json_response({"session": view.session.identity})
            # user = action.add_stat(self.handler.init_by_ref(user_link, lang=view.lang, form='CurrentUser'))
            user_id = user_link.get('_id')
            user = User(view.storage, lang=view.lang, form='CurrentUser')
            if user_id:
                user = action.add_stat(await user.find_by_id(user_link['_id'], _form=None))
            result = {
                "session": view.session.identity,
                "user_": view.session.get('user_'),
                "account": view.session.get('account'),
                "accounts": user.data.get('accounts', [])
            }
            return action.set_end(self.response.json_response(result))
            # login = view.data['login']
            # password = view.data['password']
        except KeyError as err:
            raise KeyNotFound(detail=err)

    @async_action
    async def api_sign_out(self, view, **kwargs):
        action = kwargs['_action']
        try:
            session = action.add_stat(await Session.init_from_view(view))
            await session.close()
            view.session.invalidate()
        except KeyError:  # нет сессии
            pass
        # session = await new_session(view.request)
        # session['last_visit'] = time.time()
        return action.set_end(self.response.json_response({}))

    # def _get_session_response(self, session, user):
