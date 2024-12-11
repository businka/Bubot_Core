import datetime
from bubot_helpers.ExtException import ExtException
from bubot_helpers.ActionDecorator import async_action


class ObjAction:
    def __init__(self, storage, db, session, **kwargs):
        self.data = {}
        self.db = db
        self.begin = datetime.datetime.now(datetime.timezone.utc)
        self.storage = storage
        self.session = session
        self.debug = False

    @async_action
    async def register(self, obj, action, data=None, *, begin=None, end=None, report=None, stat=None, _action=None):
        if isinstance(data, ExtException):
            error = True
            data = data.to_dict()
        else:
            error = False
        if begin is None:
            begin = self.begin
        if end is None:
            end = datetime.datetime.now(datetime.timezone.utc)
        data = dict(
            begin=begin,
            end=end,
            obj_=obj.get_link(add_obj_type=True) if obj is not None else None,
            action=action,
            error=error,
            data=data,
            stat=stat,
            user_=self.session['user_'] if self.session is not None else None
        )
        _action.add_stat(await self.storage.update(obj.db, 'action', data, create=True))

