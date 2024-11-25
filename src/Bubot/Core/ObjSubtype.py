from bubot.core.Obj import Obj
from uuid import uuid4

from bubot.core.BubotHelper import BubotHelper
from bubot.core.ObjForm import ObjForm
from bubot.core.ObjModel import ObjModel
from bubot_helpers.ActionDecorator import async_action
from bubot_helpers.ExtException import KeyNotFound
from bubot_helpers.Helper import Helper

# from .SyncObjCore import ExtObjCore


class ObjSubtype(Obj):

    # def init(self, *, app_name=None, **kwargs):
    #     self.data = dict(
    #         title=self.__class__.__name__
    #     )

    async def set_default_params(self, data):
        data['subtype'] = self.__class__.__name__
        return data
