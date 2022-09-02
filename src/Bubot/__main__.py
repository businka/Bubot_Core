import argparse
import logging

from Bubot.Helpers.ExtException import HandlerNotFoundError
from BubotObj.OcfDevice.subtype.Device.Device import Device

# from Bubot.Core import main

parser = argparse.ArgumentParser(description='IoT framework based on OCF specification')
parser.add_argument('--n', dest='class_name', default='WebServer', type=str,
                    help='OCF device class name (default: WebServer)')
parser.add_argument('--i', dest='di', type=str, help='ID of the device being launched, optional')
parser.add_argument('--p', dest='path', default='./', type=str, help='path to config dir (default: ./)')
# parser.add_argument('--l', default='./', type=str, help='path to log dir (default: ./)')
parser.add_argument('--d', dest='log_level', default='error', type=str,
                    help='log level: notset/debug/info/warning/error/critical (default: error)')
# parser.add_argument('--f', dest='log_format', default='%(levelname)s %(name)s.%(funcName)s %(message)s',
#                     type=str, help=f'logger format (default: ')
args = parser.parse_args()

logging.basicConfig(
    level=args.log_level.upper(),
    format='%(levelname)s %(name)s.%(funcName)s %(message)s'
)
try:
    device = Device.init_from_file(di=args.di, path=args.path, class_name=args.class_name)
    device.run()
except HandlerNotFoundError:
    print(f'Error: class_name {args.class_name} not found. run "bubot -h" for help')

