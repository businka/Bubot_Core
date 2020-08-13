from aiohttp import web
from BuBot.Core.FastStorage.PythonFastStorage import PythonFastStorage as FastStorage
from BuBot.Core.DataBase.Mongo import Mongo as Storage
from BuBot.Core.AuthHandler import AuthHandler
from BuBot.Core.ApiHandler import ApiHandler
from BuBot.Core.FormHandler import FormHandler
from BuBot.Core.ReportHandler import ReportHandler


def start():
    app = web.Application()
    # logging.basicConfig(level=logging.DEBUG)
    app.router.add_route('*', '/auth/login_by_cert', AuthHandler)
    app.router.add_route('*', '/api/{objType}/{objName}', ApiHandler)
    app.router.add_route('*', '/api/{objType}/{objName}/{method}', ApiHandler)
    app.router.add_route('*', '/form/{objType}/{objName}/{formName}', FormHandler)
    app.router.add_route('*', '/report/{objType}/{objName}/{reportName}/{reportSection}', ReportHandler)
    app.router.add_static('/jr', './jasper_reports')
    app['fast_storage'] = FastStorage()
    app['storage'] = Storage.connect()
    web.run_app(app, port=8081)


if __name__ == '__main__':
    start()
