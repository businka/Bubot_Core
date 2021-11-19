import socket
import asyncio
import struct
from Bubot.Core.Coap.CoapProtocol2 import CoapResource
from Bubot.Helpers.ExtException import ExtTimeoutError, CancelOperation
from random import randrange
import asyncio
import logging
from aiocoap.numbers import COAP_PORT
from aiocoap import interfaces
from aiocoap.transports.generic_udp import GenericMessageInterface
from aiocoap.util import hostportjoin
from aiocoap.protocol import Context
from aiocoap.transports.simplesocketserver import _DatagramServerSocketSimple, _Address
from aiocoap.transports.tcp import TCPClient
from aiocoap import resource
from aiocoap import interfaces, optiontypes, error, util
import aiocoap
import socket
import struct
from aiocoap import *
from aiocoap.resource import Site
from Bubot.Core.Coap.ext_aiocoap import UdpMulticastIpv4Server, UdpUnicastIpv4Server, UdpMulticastIpv6Server, \
    UdpUnicastIpv6Server, MessageInterfaceServer, OcfSite


class CoapServer(Context):
    coap_discovery_ipv6 = ['FF02::158']  # , 'FF03::158', 'FF05::158']
    coap_discovery_ipv4 = ['224.0.1.187']  # All CoAP Nodes RFC7252
    coap_timeout = 25

    def __init__(self, device, **kwargs):
        self.device = device
        self.log = device.log
        self.loop = device.loop
        self.ipv6 = self.device.get_param('/oic/con', 'udpCoapIPv6', True)
        self.ipv4 = self.device.get_param('/oic/con', 'udpCoapIPv4', False)
        self.multicast_port = 5683
        self.unicast_port = self.device.get_param('/oic/con', 'udpCoapPort', None)
        self.net_interface = self.device.get_param('/oic/con', 'NetInterface', 0)  # default interface

        root = OcfSite()
        root.add_resource(['Ocf'], CoapResource())

        self.coap = super().__init__(loop=self.loop, serversite=root, loggername="coap", client_credentials=None)

        self.resources = {}
        self.waiting_response = {}
        self.endpoint = {
            'multicast': [],
            'IPv4': {},
            'IPv6': {}
        }
        self._last_message_id = 0
        self.answer = {}

    @classmethod
    async def run(cls, device, **kwargs):
        self = cls(device)

        if self.ipv4:
            bind = ('', self.unicast_port)
            await self._append_tokenmanaged_messagemanaged_transport(
                lambda mman: MessageInterfaceServer.create_server(bind, mman, log=self.log, loop=self.loop,
                                                                  handler=UdpUnicastIpv4Server, server=self))

            bind = ('', self.multicast_port)
            await self._append_tokenmanaged_messagemanaged_transport(
                lambda mman: MessageInterfaceServer.create_server(bind, mman, log=self.log, loop=self.loop,
                                                                  handler=UdpMulticastIpv4Server, server=self))

        if self.ipv6:
            bind = ('::', self.unicast_port)
            await self._append_tokenmanaged_messagemanaged_transport(
                lambda mman: MessageInterfaceServer.create_server(bind, mman, log=self.log, loop=self.loop,
                                                                  handler=UdpUnicastIpv6Server, server=self))

            bind = ('::', self.multicast_port)
            await self._append_tokenmanaged_messagemanaged_transport(
                lambda mman: MessageInterfaceServer.create_server(bind, mman, log=self.log, loop=self.loop,
                                                                  handler=UdpMulticastIpv6Server, server=self))

        from aiocoap.transports.simple6 import MessageInterfaceSimple6
        await self._append_tokenmanaged_messagemanaged_transport(
            lambda mman: MessageInterfaceSimple6.create_client_transport_endpoint(mman, log=self.log, loop=self.loop))

        if self.device.get_param('/oic/con', 'udpCoapPort', None) != self.unicast_port:
            self.device.set_param('/oic/con', 'udpCoapPort', self.unicast_port, save_config=True)
        self.log.debug('on port {0}'.format(self.unicast_port))

        return self

    async def send_multi_answer_request(self, message, address, callback, *args):
        self.log.debug('send_multi_request {0}'.format(message.opt.uri_path))
        self.answer[message.token] = dict(
            request=message,
            response=callback,
            lock=asyncio.Lock(),
            result=args[0] if args else None
        )
        self.send_message(message, address)

    async def send_answer(self, answer):
        msg, remote = answer.encode_to_coap()
        self.send_message(msg, remote)

    async def send_request(self, message, remote, **kwargs):
        _request_description = f'{remote[0]}:{remote[1]}{message.opt.uri_path}'
        self.log.debug(_request_description)
        self.answer[message.token] = dict(
            request=message,
            response=asyncio.Future()
        )

        self.send_message(message, remote)

        timeout = kwargs.get('timeout', self.coap_timeout)
        try:
            res = await asyncio.wait_for(self.answer[message.token]['response'], timeout)
            self.log.debug('receiv_answer {0} {1}'.format(
                message.token, remote[0]))
            return res
        except KeyError:
            self.log.error('unknown')
            raise
        except asyncio.CancelledError:
            raise CancelOperation(detail=_request_description)
        except asyncio.TimeoutError:
            raise ExtTimeoutError(detail=_request_description)
        finally:
            self.answer.pop(message.token)
            pass

    def send_message(self, message, remote):
        try:
            net_index = remote[0].find('%')
        except AttributeError:
            raise ValueError('Receiver address  not defined')
        try:
            if net_index >= 0:
                remote = (remote[0][0:net_index], remote[1])  # убираем номер интерфейса из адреса
            _protocol = 'IPv6' if socket.getaddrinfo(remote[0], remote[1])[0][0] == socket.AF_INET6 else 'IPv4'
            try:
                transport = self.endpoint[_protocol]['transport']
            except KeyError:
                raise Exception(f'protocol not supported')
            raw_data = message.encode()
            self.log.debug(f'send message {message.mid} {remote}')
            transport.sendto(raw_data, remote)
            pass
        except Exception as e:
            self.log.error(e)
            raise e from None

    def close(self):
        if self.ipv6:
            self.endpoint['IPv6']['transport'].close()
        if self.ipv4:
            self.endpoint['IPv4']['transport'].close()
        for elem in self.endpoint['multicast']:
            elem['transport'].close()
