import asyncio
from datetime import datetime
from uuid import uuid4

# from bubot.core.Obj import Obj
from bubot_helpers.ActionDecorator import async_action
from bubot_helpers.ExtException import Unauthorized
from bubot_tofirstgrade.buject.OcfDevice.subtype.ToFirstGrade.SchoolApi.SchoolApi import SchoolApi
# from BubotObj.Client.SchoolApiSelenium import SchoolApiSelenium


class ObjSchema:
    # name = 'ObjSchema'
    file = __file__

