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


class UdpUnicastIpv4Server(_DatagramServerSocketSimple):
    @classmethod
    async def create2(cls, bind, log, loop, new_message_callback, new_error_callback, server):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.bind(bind)

        ready = asyncio.Future()

        transport, protocol = await loop.create_datagram_endpoint(
            lambda: cls(ready.set_result, new_message_callback, new_error_callback, log),
            sock=sock
        )

        # Conveniently, we only bind to a single port (because we need to know
        # the return address, not because we insist we know the local
        # hostinfo), and can thus store the local hostinfo without distinction
        protocol.hostinfo_local = hostportjoin(bind[0], bind[1] if bind[1] != COAP_PORT else None)


        _address = transport.get_extra_info('socket').getsockname()
        if server.unicast_port and server.unicast_port != _address[1]:
            raise Exception('IPv4 unicast port {} not installed'.format(server.unicast_port))
        _address = socket.getaddrinfo(socket.gethostname(), _address[1], socket.AF_INET, socket.SOCK_DGRAM)[0][4]
        server.unicast_port = _address[1]
        server.endpoint['IPv4'] = dict(
            transport=transport,
            protocol=protocol,
            address=_address,
            uri='coap://{0}:{1}'.format(_address[0], _address[1])
        )

        return await ready


class UdpMulticastIpv4Server(_DatagramServerSocketSimple):
    @classmethod
    async def create2(cls, bind, log, loop, new_message_callback, new_error_callback, server):
        # if bind is None or bind[0] in ('::', '0.0.0.0', '', None):
        #     raise ValueError("The transport can not be bound to any-address.")

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(bind)
        for group in ['224.0.1.187']:
            sock.setsockopt(
                socket.IPPROTO_IP,
                socket.IP_ADD_MEMBERSHIP,
                struct.pack(
                    "=4sl",
                    socket.inet_aton(group),
                    socket.INADDR_ANY
                )
            )
        ready = asyncio.Future()

        transport, protocol = await loop.create_datagram_endpoint(
            lambda: cls(ready.set_result, new_message_callback, new_error_callback, log),
            sock=sock
        )

        # Conveniently, we only bind to a single port (because we need to know
        # the return address, not because we insist we know the local
        # hostinfo), and can thus store the local hostinfo without distinction
        protocol.hostinfo_local = hostportjoin(bind[0], bind[1] if bind[1] != COAP_PORT else None)

        return await ready


class UdpUnicastIpv6Server(_DatagramServerSocketSimple):
    @classmethod
    async def create2(cls, bind, log, loop, new_message_callback, new_error_callback, server):
        sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # sock.setsockopt(41, socket.IPV6_V6ONLY, 0)
        sock.bind(bind)

        ready = asyncio.Future()

        transport, protocol = await loop.create_datagram_endpoint(
            lambda: cls(ready.set_result, new_message_callback, new_error_callback, log),
            sock=sock
        )

        # Conveniently, we only bind to a single port (because we need to know
        # the return address, not because we insist we know the local
        # hostinfo), and can thus store the local hostinfo without distinction
        protocol.hostinfo_local = hostportjoin(bind[0], bind[1] if bind[1] != COAP_PORT else None)

        _address = transport.get_extra_info('socket').getsockname()
        if server.unicast_port and server.unicast_port != _address[1]:
            raise Exception('IPv6 unicast port {} not installed'.format(server.unicast_port))
        _address = socket.getaddrinfo(socket.gethostname(), _address[1], socket.AF_INET6, socket.SOCK_DGRAM)[0][4]

        server.unicast_port = _address[1]
        server.endpoint['IPv6'] = dict(
            transport=transport,
            protocol=protocol,
            address=_address,
            uri='coap://[{0}]:{1}'.format(_address[0], _address[1])
        )

        return await ready


class UdpMulticastIpv6Server(_DatagramServerSocketSimple):
    @classmethod
    async def create2(cls, bind, log, loop, new_message_callback, new_error_callback, server):
        interface_index = 0  # default

        sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        # sock.setsockopt(41, socket.IPV6_V6ONLY, 0)
        sock.bind(bind)
        # sock.bind(('::', port))
        for group in ['FF02::158']:
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
        ready = asyncio.Future()

        transport, protocol = await loop.create_datagram_endpoint(
            lambda: cls(ready.set_result, new_message_callback, new_error_callback, log),
            sock=sock
        )

        # Conveniently, we only bind to a single port (because we need to know
        # the return address, not because we insist we know the local
        # hostinfo), and can thus store the local hostinfo without distinction
        protocol.hostinfo_local = hostportjoin(bind[0], bind[1] if bind[1] != COAP_PORT else None)

        return await ready


class MessageInterfaceServer(GenericMessageInterface):
    @classmethod
    async def create_server(cls, bind, ctx: interfaces.MessageManager, log, loop, handler, server):
        self = cls(ctx, log, loop)
        bind = bind or ('::', None)
        # Interpret None as 'default port', but still allow to bind to 0 for
        # servers that want a random port (eg. when the service URLs are
        # advertised out-of-band anyway). LwM2M clients should use simple6
        # instead as outlined there.
        bind = (bind[0], COAP_PORT if bind[1] is None else bind[1])

        self._pool = await handler.create2(bind, log, self._loop,
                                           self._received_datagram, self._received_exception,
                                           server)

        return self

    async def recognize_remote(self, remote):
        try:
            return isinstance(remote, _Address) and remote in remote.serversocket is self._pool
        except:
            return False


class OcfContext(Context):
    @classmethod
    async def create_server_context2(cls, server, site, **kwargs):
        loop = kwargs.get('loop', asyncio.get_event_loop())
        loggername = kwargs.get('loggername', 'coap')

        port = 40404
        multicast_port = 5683

        self = cls(loop=loop, serversite=site, loggername=loggername)

        bind = ('', port)
        await self._append_tokenmanaged_messagemanaged_transport(
            lambda mman: MessageInterfaceServer.create_server(bind, mman, log=self.log, loop=loop,
                                                              handler=UdpUnicastIpv4Server))

        bind = ('', multicast_port)
        await self._append_tokenmanaged_messagemanaged_transport(
            lambda mman: MessageInterfaceServer.create_server(bind, mman, log=self.log, loop=loop,
                                                              handler=UdpMulticastIpv4Server))

        bind = ('::', port)
        await self._append_tokenmanaged_messagemanaged_transport(
            lambda mman: MessageInterfaceServer.create_server(bind, mman, log=self.log, loop=loop,
                                                              handler=UdpUnicastIpv6Server))

        bind = ('::', multicast_port)
        await self._append_tokenmanaged_messagemanaged_transport(
            lambda mman: MessageInterfaceServer.create_server(bind, mman, log=self.log, loop=loop,
                                                              handler=UdpMulticastIpv6Server))

        from aiocoap.transports.simple6 import MessageInterfaceSimple6
        await self._append_tokenmanaged_messagemanaged_transport(
            lambda mman: MessageInterfaceSimple6.create_client_transport_endpoint(mman, log=self.log, loop=loop))

        return self


class OcfSite(Site):
    def _find_child_and_pathstripped_message(self, request):
        """Given a request, find the child that will handle it, and strip all
        path components from the request that are covered by the child's
        position within the site. Returns the child and a request with a path
        shortened by the components in the child's path, or raises a
        KeyError.

        While producing stripped messages, this adds a ._original_request_uri
        attribute to the messages which holds the request URI before the
        stripping is started. That allows internal components to access the
        original URI until there is a variation of the request API that allows
        accessing this in a better usable way."""

        original_request_uri = getattr(request, '_original_request_uri',
                                       request.get_request_uri(local_is_server=True))

        stripped = request.copy(uri_path=())
        stripped._original_request_uri = original_request_uri
        handler = self._resources[tuple(['Ocf'])]
        return handler, stripped
