import asyncio
from asyncio import TimeoutError
from socket import AF_INET, AF_INET6
from urllib.parse import urlparse
from uuid import UUID

from Bubot_CoAP import defines
from Bubot_CoAP.messages.numbers import NON, Code, ACK
from Bubot_CoAP.messages.option import Option
from Bubot_CoAP.messages.request import Request
from Bubot_CoAP.messages.response import Response
from Bubot_CoAP.server import Server
from Bubot_CoAP.utils import calc_family_by_address
from bubot.core.ResourceLink import ResourceLink
from bubot_helpers.ExtException import ExtException, ExtTimeoutError, KeyNotFound
from .CloudCoapTcpClient import CloudCoapTcpClient


class TransportLayer:
    coap_discovery = {AF_INET6: ['FF02::158'], AF_INET: ['224.0.1.187']}
    coap_discovery_port = 5683

    def __init__(self, device):
        self.device = device
        self.coap: Server = None
        self.cloud: CloudCoapTcpClient = None
        self.ipv6 = None
        self.ipv4 = None
        self.ipv6ssl = None
        self.ipv4ssl = None

    async def start(self):
        self.coap = Server()
        await self.start_coap()
        self.cloud = CloudCoapTcpClient(self.device, self.coap)
        ...
        # server.add_resource('/oic/sec/doxm', BasicResource('test', server))

    async def stop(self):
        tasks = []
        if self.coap:
            tasks.append(self.coap.close())
        if self.cloud:
            tasks.append(self.cloud.disconnect())
        await asyncio.gather(*tasks)

    def secure_socket_props(self):
        return dict(
            identity_hint=UUID(self.device.di).bytes,
            # todo device init - check id is uuid
            psk=None,
            ciphers=None
        )

    async def start_coap(self):
        try:
            self.ipv6 = self.device.get_param('/oic/con', 'udpCoapIPv6', '::')
            self.ipv4 = self.device.get_param('/oic/con', 'udpCoapIPv4', '')
            if self.ipv6 is None and self.ipv4 is None:
                return
            for href in self.device.res:
                self.coap.root[href] = self.device.res[href]
                # self.coap.add_resource(href, self.device.res[href])
                # pass

            self.ipv6ssl = self.device.get_param('/oic/con', 'udpCoapIPv6Ssl', True)
            self.ipv4ssl = self.device.get_param('/oic/con', 'udpCoapIPv4Ssl', True)
            certfile = f'{self.device.path}/bubot_cert.pem'
            keyfile = f'{self.device.path}/bubot_key.pem'

            unicast_port = self.device.get_param('/oic/con', 'udpCoapPort', None)
            unicast_ssl_port = self.device.get_param('/oic/con', 'udpCoapSslPort', None)
            if self.ipv4 is not None:
                res = await self.coap.add_endpoint(f'coap://{self.ipv4}:{unicast_port}',
                                                   multicast=True,
                                                   multicast_addresses=self.coap_discovery[AF_INET],
                                                   multicast_port=self.coap_discovery_port)
                real_unicast_port = res[0].address[1]
                if not unicast_port or unicast_port != real_unicast_port:
                    self.device.log.info(f'change coap port {real_unicast_port}')
                    self.device.set_param('/oic/con', 'udpCoapPort', real_unicast_port)
                pass

                if self.ipv4ssl:
                    res = await self.coap.add_endpoint(f'coaps://{self.ipv4}:{unicast_ssl_port}',
                                                       multicast=False,
                                                       multicast_addresses=self.coap_discovery[AF_INET],
                                                       multicast_port=self.coap_discovery_port,
                                                       keyfile=keyfile,
                                                       certfile=certfile,
                                                       socket_props=self.secure_socket_props())
                    real_unicast_port = res[0].address[1]
                    if not unicast_port or unicast_port != real_unicast_port:
                        self.device.log.info(f'change ssl coap port {real_unicast_port}')
                        self.device.set_param('/oic/con', 'udpCoapSslPort', real_unicast_port)

            if self.ipv6 is not None:
                res = await self.coap.add_endpoint(f'coap://[{self.ipv6}]:{unicast_port}',
                                                   multicast=True,
                                                   multicast_addresses=self.coap_discovery[AF_INET6],
                                                   multicast_port=self.coap_discovery_port)
                if not unicast_port:
                    unicast_port = res[0].address[1]
                    self.device.set_param('/oic/con', 'udpCoapPort', unicast_port)

                if self.ipv6ssl:
                    res = await self.coap.add_endpoint(f'coaps://[::]:{unicast_ssl_port}',
                                                       multicast=False,
                                                       multicast_addresses=self.coap_discovery[AF_INET6],
                                                       multicast_port=self.coap_discovery_port,
                                                       keyfile=keyfile,
                                                       certfile=certfile,
                                                       socket_props=self.secure_socket_props())
                    if not unicast_ssl_port:
                        unicast_ssl_port = res[0].address[1]
                        self.device.set_param('/oic/con', 'udpCoapSslPort', unicast_ssl_port)
        except Exception as err:
            raise ExtException(
                action='start_coap',
                dump={
                    'device_id': self.device.di,
                    'device': self.device.__class__.__name__
                },
                parent=err
            )

    async def restart_coaps_endpoints(self):
        secure_schemas = ['coaps', 'coaps+tcp']
        for scheme in secure_schemas:
            secure_endpoints = self.coap.endpoint_layer.unicast_endpoints.get(scheme, {})
            for family in secure_endpoints:
                for host in secure_endpoints[family]:
                    for port in secure_endpoints[family][host]:
                        endpoint = secure_endpoints[family][host][port]
                        endpoint.params['socket_props'] = self.secure_socket_props()
                        await endpoint.restart_transport(self.coap)

    async def discovery_resource(self, *, timeout=45, owned=False, query=None, **kwargs):
        '''
        :param query:
        :param timeout:
        :param owned:

        :param kwargs:
        :return:
        '''

        async def discover():
            try:
                _protocol = []
                if self.ipv4 is not None:
                    _protocol.append(self.eps_coap_ipv4)
                if self.ipv6 is not None:
                    _protocol.append(self.eps_coap_ipv6)
                _res = None
                _token = self.coap.message_layer.fetch_token()
                _mid = self.coap.message_layer.fetch_mid()
                for elem in _protocol:
                    for ip in elem:
                        for port in elem[ip]:
                            ep = elem[ip][port]
                            async with ep.lock:
                                request = Request()
                                request.token = _token
                                request.mid = _mid
                                request.uri_path = '/oic/sec/doxm'
                                request.query = _query
                                request.type = NON
                                request.code = Code.GET
                                # request.content_type = 10000
                                request.accept = 10000
                                request.source = ep.address
                                request.multicast = True
                                request.family = ep.family
                                request.scheme = ep.scheme

                                option = Option(defines.OptionRegistry.OCF_ACCEPT_CONTENT_FORMAT_VERSION, 2048)
                                request.add_option(option)

                                request.destination = (self.coap_discovery[ep.family][0], self.coap_discovery_port)
                                _res = asyncio.create_task(self.coap.send_message(request, timeout=timeout))
                                await asyncio.sleep(0)
                                # _res.append(self.coap.send_message(request))
                return await _res  # все вернется одновременно потому что токен один
            except Exception as err:
                raise ExtException(parent=err)

        async def get_eps(_result, net_interface):
            try:
                _request = Request()
                _request.type = NON
                _request.code = Code.GET
                _request.uri_path = '/oic/res'
                _request.query = {'rt': ['oic.r.doxm']}
                _request.content_type = 10000

                _request.source = _msg.destination
                _request.family = _msg.family
                _request.scheme = _msg.scheme
                _request.destination = _msg.source
                _resp = await self.coap.send_message(_request)
                _payload = _resp.decode_payload()
                if len(_payload) > 1:
                    self.device.log.error(f'not supported answer /oic/res. {_result.get("di")}')
                _payload = _payload[0]
                # result[di]['res'] = json.dumps(_payload)  # for debug
                _eps = []
                if 'links' in _payload:
                    _link = _payload['links']
                    if 'eps' in _link:  # todo надо узнать по старому формату eps может быть вообще?
                        _eps = _link['eps']
                    else:
                        _eps.append({
                            'ep': f'{_msg.family}://{_msg.source[0]}:{_msg.source[1]}'})
                        try:
                            if 'p' in _link and _link['p'].get('sec') and _link['p'].get('port'):
                                _eps.append({'ep': f'coaps://{_msg.source[0]}:{_link["p"]["port"]}'})
                        except Exception:
                            pass
                else:
                    _eps = _payload['eps']
                _result['eps'] = []
                for elem in _eps:
                    elem['net_interface'] = net_interface
                    # _url = urlparse(elem['ep'])
                    # _address = _url.netloc.split(":")
                    # _result['eps'].append({
                    #     '_id': _url.scheme,
                    #     'scheme': _url.scheme,
                    #     'host': _address[0],
                    #     'port': int(_address[1]),
                    #     'path': _url.path,
                    #     'net_interface': net_interface
                    # })
                _result['eps'] = _eps
            except Exception as err:
                raise ExtException(parent=err)

        async def get_name(_result):
            try:
                _request = Request()
                _request.type = NON
                _request.code = Code.GET
                _request.uri_path = '/oic/d'
                _request.content_type = 10000
                _request.source = _msg.destination
                _request.family = _msg.family
                _request.scheme = _msg.scheme
                _request.destination = _msg.source
                resp = await self._send_message(_request)
                _payload = resp.decode_payload()
                # result[di]['oic-d'] = json.dumps(_payload)  # debug
                _result['n'] = _payload.get('n')
                _result['di'] = _payload.get('di')
                if not _result['n'] or not _result['di']:
                    self.device.log.error(f'Bad answer name {_payload}')
            except Exception as err:
                raise ExtException(parent=err, message="Bad answer from device", detail=item['di'])

        try:
            result = []
            _query = query if query else {}
            if owned is not None:
                _query['owned'] = ['TRUE'] if owned else ['FALSE']
            # _address_index = {}
            self.device.log.debug(f'start discover device {_query}')
            _list_res = await discover()
            self.device.log.debug(f'end discover device {_query}, found {len(_list_res)}')
            for _msg in _list_res:
                payload = _msg.decode_payload()
                # if not payload:
                #     continue  # todo что то сделать с ошибками

                di = payload['deviceuuid'] if payload else ''
                item = {
                    'di': di
                }
                try:
                    await get_eps(item, _msg.destination[0])
                except Exception as err:
                    e = ExtException(parent=err)
                    self.device.log.error(f'for found device {di} read eps fault {e}')
                    continue
                try:
                    await get_name(item)
                except Exception as err:
                    e = ExtException(parent=err)
                    self.device.log.error(f'for found device {di} read name: {e}')
                    continue
                result.append(item)

            return result

        except Exception as err:
            raise ExtException(parent=err)

    async def find_device(self, di, *, owned=None, timeout=30):
        try:
            links = await self.discovery_resource(
                query=dict(di=[di]),
                timeout=timeout,
                owned=owned
            )
            if isinstance(links, list):
                for _link in links:
                    if _link['di'] == di:
                        return _link
            return None
        except Exception as err:
            raise ExtException(parent=err)

    async def find_resource_by_link(self, link, timeout=30):
        try:
            self.device.log.debug('find resource by di {0} href {1}'.format(link.di, link.href))

            links = await self.discovery_resource(
                query=dict(di=[link.di], href=[link.href]), timeout=timeout
            )
            if isinstance(links, list):
                for _link in links:
                    if _link['di'] == link.di:  # todo переделать
                        found_link = ResourceLink.init(link)
                        found_link.href = link.href
                        return _link
                        # for ref in links[di].links:
                        #     if ref == link.href:
                        #         return links[di].links[ref]
            return None
        except Exception as err:
            raise ExtException(parent=err, action='find_resource_by_link')

    @property
    def eps_coap_ipv4(self):
        if not self.coap:
            return []
        try:
            return self.coap.endpoint_layer.unicast_endpoints['coap'][AF_INET]
        except KeyError:
            return []

    @property
    def eps_coap_ipv6(self):
        if not self.coap:
            return []
        try:
            return self.coap.endpoint_layer.unicast_endpoints['coap'][AF_INET6]
        except KeyError:
            return []

    def get_eps(self, _host=None, _scheme=None):
        def add_ep(ep_host):
            ep = self.coap.endpoint_layer.unicast_endpoints[scheme][protocol][ep_host][port]
            if ep.is_client:
                return
            if protocol == AF_INET6:
                _eps.append({'ep': f'{scheme}://[{ep_host}]:{port}'})
            else:
                _eps.append({'ep': f'{scheme}://{ep_host}:{port}'})

        _eps = []
        if not self.coap:
            return _eps
        if _scheme:
            unicast_eps = {_scheme: self.coap.endpoint_layer.unicast_endpoints[_scheme]}
        else:
            unicast_eps = self.coap.endpoint_layer.unicast_endpoints
        for scheme in unicast_eps:
            for protocol in self.coap.endpoint_layer.unicast_endpoints[scheme]:
                if _host:
                    for port in self.coap.endpoint_layer.unicast_endpoints[scheme][protocol].get(_host, []):
                        add_ep(_host)
                else:
                    for host in self.coap.endpoint_layer.unicast_endpoints[scheme][protocol]:
                        for port in self.coap.endpoint_layer.unicast_endpoints[scheme][protocol][host]:
                            add_ep(host)
        return _eps

    @staticmethod
    def map_coap_code_to_crudn(code):
        map_coap_to_crudn = {
            'post': 'update',
            'put': 'create',
            'delete': 'delete',
            'get': 'retrieve'
        }
        try:
            return map_coap_to_crudn[code.lower()]
        except KeyError:
            raise Exception('Unknown CRUDN operation ({0})'.format(code))

    @staticmethod
    def map_crudn_to_coap_code(operation):
        #    +------+--------+-----------+
        #    | Code | Name   | Reference |
        #    | 0.01 | GET    | [RFC7252] |
        #    | 0.02 | POST   | [RFC7252] |
        #    | 0.03 | PUT    | [RFC7252] |
        #    | 0.04 | DELETE | [RFC7252] |
        #    +------+--------+-----------+
        map_crudn_to_coap = {
            'create': 3,
            'get': 1,
            'retrieve': 1,
            'post': 2,
            'update': 2,
            'delete': 4,
        }
        return map_crudn_to_coap[operation.lower()]

    async def send_raw_data(self, to, data, **kwargs):
        secure = kwargs.get('secure', False)
        scheme = 'coaps' if secure else 'coap'
        family = to['family']
        net_interface = to['net_interface']

        _tmp = self.coap.endpoint_layer.unicast_endpoints[scheme][family][net_interface]
        ep = _tmp[list(_tmp.keys())[0]]
        ep.sock.sendto(data, to[scheme])

    def _prepare_request(self, operation, to, data=None, *, ack=False, secure=False, multicast=False, query=None,
                         href=None, **kwargs):
        try:
            if secure:
                scheme = 'coaps'
                ep = to.get_endpoint_by_scheme(scheme)
                if not ep:
                    scheme = 'coap'
                    ep = to.get_endpoint_by_scheme(scheme)
            else:
                scheme = 'coap'
                ep = to.get_endpoint_by_scheme(scheme)

            dest = urlparse(ep['ep'])
            dest_address = (dest.hostname, dest.port)
            family, dest_address = calc_family_by_address(dest_address)

            request = Request()
            request.type = ACK if ack else NON
            request.scheme = scheme
            request.multicast = multicast
            request.family = family

            if multicast:
                request.destination = (self.coap_discovery[family][0], self.coap_discovery_port)
            else:
                try:
                    request.source = (ep.get('net_interface'), None)
                    request.destination = dest_address
                except (KeyError, TypeError) as err:
                    raise KeyNotFound(message='Endpoint param not defined', detail=err)

            request.code = self.map_crudn_to_coap_code(operation)
            request.uri_path = href or to.get('href', '')

            request.add_option(Option(defines.OptionRegistry.CONTENT_TYPE, 10000))

            # request.accept = 10000

            # query = kwargs.get('query')
            if query:
                request.query = query

            if data:
                request.encode_payload(data)
            return request
        except Exception as err:
            raise ExtException(parent=err)

    # def get_endpoint(self, to, *, secure=False, scheme=None):
    #     request = self._prepare_request('get', to, data=None, secure=secure)
    #     endpoint = self.coap.endpoint_layer.find_sending_endpoint(request)
    #     return endpoint

    async def _send_message(self, request, **kwargs):
        try:
            response: Response = await self.coap.send_message(request, **kwargs)
            if not isinstance(response, Response):
                ...
            if response.is_error():
                payload = response.decode_payload()
                if payload:
                    raise ExtException(parent=payload)
                else:
                    code = defines.Codes.LIST.get(response.code)
                    raise ExtException(message=code.name if code else f'CoAP error {response.code}')
            return response
        except (TimeoutError, asyncio.TimeoutError):
            raise ExtTimeoutError()
        # except ExtException as err:
        #     raise ExtException(parent=err,
        #                        action=f'{self.__class__.__name__}.request()',
        #                        dump=dict(op=operation, to=str(to), data=data, kwargs=kwargs))
        except Exception as err:
            raise ExtException(parent=err)

    async def send_message(self, operation, to, data=None, *, ack=False, secure=False, multicast=False, query=None,
                           **kwargs):
        if not self.coap:
            raise ExtException(message='coap server not initialized')
        try:
            request = self._prepare_request(operation, to, ack=ack,
                                            data=data, secure=secure, multicast=multicast, query=query, **kwargs)

            return await self._send_message(request, **kwargs)
        except Exception as err:
            raise ExtException(parent=err,
                               action='{}.request()'.format(self.__class__.__name__),
                               dump=dict(op=operation, to=str(to), data=data, kwargs=kwargs))
