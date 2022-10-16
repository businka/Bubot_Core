from typing import Optional, Type

from Bubot.Core.Obj import Obj
from Bubot.Helpers.Action import Action
from Bubot.Helpers.ActionDecorator import async_action
from Bubot.Core.ObjApi import ObjApi


class ObjSubtypeApi(ObjApi):

    async def prepare_json_request(self, view, **kwargs):
        handler, data = await super().prepare_json_request(view, **kwargs)
        if handler:
            try:
                subtype = data['subtype']
            except (KeyError, TypeError):
                subtype = None
            handler = handler.init_subtype(subtype)
            handler.init()
        return handler, data


