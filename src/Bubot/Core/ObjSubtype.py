from Bubot.Core.Obj import Obj
from uuid import uuid4

from Bubot.Core.BubotHelper import BubotHelper
from Bubot.Core.ObjForm import ObjForm
from Bubot.Core.ObjModel import ObjModel
from Bubot.Helpers.ActionDecorator import async_action
from Bubot.Helpers.ExtException import KeyNotFound
from Bubot.Helpers.Helper import Helper

# from .SyncObjCore import ExtObjCore


class ObjSubtype(Obj):

    def init(self, *, app_name=None, **kwargs):
        self.data = dict(
            title=self.__class__.__name__
        )

    async def set_default_params(self, data):
        data['subtype'] = self.__class__.__name__
        return data
