from aiohttp import web

from Bubot.Helpers.Helper import Helper


class ReportHandler(web.View):
    def __init__(self, request):
        web.View.__init__(self, request)
        self.obj_type = self.request.match_info.get('objType')
        self.obj_name = self.request.match_info.get('objName')
        self.report_name = self.request.match_info.get('reportName')
        self.report_section = self.request.match_info.get('reportSection')
        try:
            self.handler = Helper.get_obj_class(f'jay.{self.obj_type}.{self.obj_name}', 'reports', self.report_name)()
        except Exception as err:
            raise err

    async def get(self):
        try:
            handler = getattr(self.handler, self.report_section)
            return await handler(self)
        except Exception as err:
            return web.HTTPInternalServerError(text=str(err))
