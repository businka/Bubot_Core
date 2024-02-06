from typing import Optional
from urllib.parse import unquote

from bubot.core.Obj import Obj
from bubot.core.ObjApi import ObjApi
from bubot_helpers.Action import Action
from bubot_helpers.ActionDecorator import async_action
from bubot_helpers.ExtException import KeyNotFound, AccessDenied
from .User import User


class UserApi(ObjApi):
    handler: User = User

