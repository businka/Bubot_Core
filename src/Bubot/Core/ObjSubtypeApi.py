from typing import Optional, Type

from bubot.core.Obj import Obj
from bubot_helpers.Action import Action
from bubot_helpers.ActionDecorator import async_action
from bubot.core.ObjApi import ObjApi


class ObjSubtypeApi(ObjApi):
    pass
    # async def prepare_json_request(self, view, **kwargs):
    #     handler, data = await super().prepare_json_request(view, **kwargs)
    #     if handler:
    #         try:
    #             subtype = data['subtype']
    #         except (KeyError, TypeError):
    #             subtype = None
    #         handler = handler.init_subtype(subtype)
    #         handler.init()
    #     return handler, data


