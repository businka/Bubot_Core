import logging
import os.path

from bubot.buject.OcfDevice.subtype.VirtualServer.VirtualServer import VirtualServer

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.ERROR,
        format='%(levelname)s %(name)s.%(funcName)s %(message)s'
    )
    _path = os.path.join(os.path.dirname(__file__), 'conf')
    device = VirtualServer.init_from_file(path=_path)
    device.run()
