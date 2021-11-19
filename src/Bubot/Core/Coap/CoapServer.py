import socket
import asyncio
import struct
from Bubot.Core.Coap.CoapProtocol import CoapProtocol
from Bubot.Helpers.ExtException import ExtTimeoutError, CancelOperation
from random import randrange



class CoapServer:
    coap_discovery_ipv6 = ['FF02::158']  # , 'FF03::158', 'FF05::158']
    coap_discovery_ipv4 = ['224.0.1.187']  # All CoAP Nodes RFC7252
    coap_timeout = 25

    def __init__(self, device):
        self.device = device
        self._mid = randrange(0xfe)
        self._token = randrange(0xfffe)
        self.log = device.log
        self.loop = device.loop
        self.ipv6 = self.device.get_param('/oic/con', 'udpCoapIPv6', True)
        self.ipv4 = self.device.get_param('/oic/con', 'udpCoapIPv4', False)
        self.multicast_port = 5683
        self.unicast_port = self.device.get_param('/oic/con', 'udpCoapPort', None)
        self.net_interface = self.device.get_param('/oic/con', 'NetInterface', 0)  # default interface

        self.resources = {}
        self.waiting_response = {}
        self.endpoint = {
            'multicast': [],
            'IPv4': {},
            'IPv6': {}
        }
        self._last_message_id = 0
        self.answer = {}

    @property
    def token(self):
        self._token = (self._token + 1) & 0xff
        return self._token

    @property
    def mid(self):
        self._mid = (self._mid + 1) & 0xffff
        return self._mid

    async def run(self):
        if self.ipv6:
            await self.run_multicast_ipv6(CoapProtocol, self.coap_discovery_ipv6, self.multicast_port)
            await self.run_unicast_ipv6(CoapProtocol, self.unicast_port)
        if self.ipv4:
            await self.run_multicast_ipv4(CoapProtocol, self.coap_discovery_ipv4, self.multicast_port)
            await self.run_unicast_ipv4(CoapProtocol, self.unicast_port)
        pass
        if self.device.get_param('/oic/con', 'udpCoapPort', None) != self.unicast_port:
            self.device.set_param('/oic/con', 'udpCoapPort', self.unicast_port, save_config=True)
        self.log.debug('on port {0}'.format(self.unicast_port))

    async def run_multicast_ipv6(self, protocol_factory, address, port):
        try:
            interface_index = 0  # default

            sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            # sock.setsockopt(41, socket.IPV6_V6ONLY, 0)
            sock.bind(('::', port))
            # sock.bind(('::', port))
            for group in address:
                sock.setsockopt(
                    41,  # socket.IPPROTO_IPV6 = 41 - not found in windows 10, bug python
                    socket.IPV6_JOIN_GROUP,
                    struct.pack(
                        '16si',
                        socket.inet_pton(socket.AF_INET6, group),
                        interface_index
                    )
                )
            sock.setsockopt(41, socket.IPV6_MULTICAST_LOOP, 1)
            _transport, _protocol = await self.loop.create_datagram_endpoint(
                lambda: protocol_factory(self, multicast=True),
                sock=sock,
            )
            # _address = _transport.get_extra_info('socket').getsockname()
            self.endpoint['multicast'].append(
                dict(
                    transport=_transport,
                    protocol=_protocol,
                    # uri='coap://[{0}]:{1}'.format(_address[0], _address[1])
                )
            )
        except Exception as e:
            self.log.error(e)
            raise e from None

    async def run_multicast_ipv4(self, protocol_factory, address, port):
        # interface_index = 0  # default
        # addrinfo = socket.getaddrinfo(address[0], None)[0]
        # sock = socket.socket(addrinfo[0], socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        # group_bin = socket.inet_pton(addrinfo[0], addrinfo[4][0])
        sock.bind(('', port))
        # mreq = group_bin + struct.pack('=I', socket.INADDR_ANY)
        # sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        for group in address:
            sock.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_ADD_MEMBERSHIP,
                struct.pack(
                    "4sl",
                    socket.inet_aton(group),
                    socket.INADDR_ANY
                )
            )
        _transport, _protocol = await self.loop.create_datagram_endpoint(
            lambda: protocol_factory(self, multicast=True),
            sock=sock,
        )
        self.endpoint['multicast'].append(
            dict(
                transport=_transport,
                protocol=_protocol,
                # uri='coap://[{0}]:{1}'.format(_address[0], _address[1])
            )
        )

    async def run_unicast_ipv6(self, protocol_factory, port=None):
        try:
            interface_index = 0  # default
            sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # sock.setsockopt(41, socket.IPV6_V6ONLY, 0)
            sock.bind(('::', port))
            _transport, _protocol = await self.loop.create_datagram_endpoint(
                lambda: protocol_factory(self, multicast=True),
                sock=sock,
            )

            _address = _transport.get_extra_info('socket').getsockname()
            if self.unicast_port and self.unicast_port != _address[1]:
                raise Exception('IPv6 unicast port {} not installed'.format(self.unicast_port))
            _address = socket.getaddrinfo(socket.gethostname(), _address[1], socket.AF_INET6, socket.SOCK_DGRAM)[0][4]

            self.unicast_port = _address[1]
            self.endpoint['IPv6'] = dict(
                transport=_transport,
                protocol=_protocol,
                address=_address,
                uri='coap://[{0}]:{1}'.format(_address[0], _address[1])
            )
            pass
        except Exception as e:
            self.log.error(e)
            raise e from None

    async def run_unicast_ipv4(self, protocol_factory, port=None):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.bind(('', port))
        _transport, _protocol = await self.loop.create_datagram_endpoint(
            lambda: protocol_factory(self),
            sock=sock
        )
        _address = _transport.get_extra_info('socket').getsockname()
        if self.unicast_port and self.unicast_port != _address[1]:
            raise Exception('IPv4 unicast port {} not installed'.format(self.unicast_port))
        _address = socket.getaddrinfo(socket.gethostname(), _address[1], socket.AF_INET, socket.SOCK_DGRAM)[0][4]
        self.unicast_port = _address[1]
        self.endpoint['IPv4'] = dict(
            transport=_transport,
            protocol=_protocol,
            address=_address,
            uri='coap://{0}:{1}'.format(_address[0], _address[1])
        )

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
