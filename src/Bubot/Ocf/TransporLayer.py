import asyncio
from socket import AF_INET, AF_INET6
from urllib.parse import urlparse
from uuid import UUID

from Bubot.Helpers.ExtException import ExtException, ExtTimeoutError
from Bubot_CoAP import defines
from Bubot_CoAP.messages.numbers import NON, Code
from Bubot_CoAP.messages.option import Option
from Bubot_CoAP.messages.request import Request
from Bubot_CoAP.server import Server


class TransportLayer:
    coap_discovery = {AF_INET6: ['FF02::158'], AF_INET: ['224.0.1.187']}
    coap_discovery_port = 5683

    def __init__(self, device):
        self.device = device
        self.coap = None
        self.ipv6 = None
        self.ipv4 = None
        self.ipv6ssl = None
        self.ipv4ssl = None

    async def start(self):
        self.coap = Server()
        await self.start_coap()

        # server.add_resource('/oic/sec/doxm', BasicResource('test', server))

    async def stop(self):
        if self.coap:
            await self.coap.close()

    async def start_coap(self):
        try:
            for href in self.device.res:
                self.coap.root[href] = self.device.res[href]
                # self.coap.add_resource(href, self.device.res[href])
                # pass

            self.ipv6 = self.device.get_param('/oic/con', 'udpCoapIPv6', '::')
            self.ipv4 = self.device.get_param('/oic/con', 'udpCoapIPv4', '')
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
                if not unicast_port:
                    unicast_port = res[0].address[1]
                    self.device.set_param('/oic/con', 'udpCoapPort', unicast_port)
                pass

                if self.ipv4ssl:
                    res = await self.coap.add_endpoint(f'coaps://{self.ipv4}:{unicast_ssl_port}',
                                                       multicast=False,
                                                       multicast_addresses=self.coap_discovery[AF_INET],
                                                       multicast_port=self.coap_discovery_port,
                                                       keyfile=keyfile,
                                                       certfile=certfile,
                                                       socket_props=dict(
                                                           identity_hint=UUID(self.device.get_device_id()).bytes,  # todo device init - check id is uuid
                                                           psk=None,
                                                           ciphers=None
                                                       ))
                    if not unicast_ssl_port:
                        unicast_ssl_port = res[0].address[1]
                        self.device.set_param('/oic/con', 'udpCoapSslPort', unicast_ssl_port)

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
                                                       certfile=certfile
                                                       )
                    if not unicast_ssl_port:
                        unicast_ssl_port = res[0].address[1]
                        self.device.set_param('/oic/con', 'udpCoapSslPort', unicast_ssl_port)
        except Exception as err:
            raise ExtException(
                action='start_coap',
                dump={
                    'device_id': self.device.get_device_id(),
                    'device': self.device.__class__.__name__
                },
                parent=err
            )

    async def discovery_resource(self, **kwargs):
        '''

        :param kwargs:
        :return:
        '''

        async def discover():
            timeout = kwargs.get('timeout')
            _protocol = []
            if self.ipv4:
                _protocol.append(self.eps_coap_ipv4)
            if self.ipv6:
                _protocol.append(self.eps_coap_ipv6)
            _res = None
            _token = self.coap.message_layer.fetch_token()
            _mid = self.coap.message_layer.fetch_mid()
            for elem in _protocol:
                for ip in elem:
                    for port in elem[ip]:
                        ep = elem[ip][port]
                        request = Request()
                        request.token = _token
                        request.query = {'owned': ['TRUE'] if kwargs.get('owned') else ['FALSE']}
                        request.mid = _mid
                        request.type = NON
                        request.code = Code.GET
                        request.uri_path = '/oic/sec/doxm'
                        # request.content_type = 10000
                        request.accept = 10000
                        request.source = ep.address
                        request.multicast = True
                        request.family = ep.family
                        request.scheme = ep.scheme

                        option = Option()
                        option.number = defines.OptionRegistry.OCF_ACCEPT_CONTENT_FORMAT_VERSION.number
                        option.value = 2048
                        request.add_option(option)

                        request.destination = (self.coap_discovery[ep.family][0], self.coap_discovery_port)
                        _res = asyncio.create_task(self.coap.send_message(request, timeout=timeout))
                        # _res.append(self.coap.send_message(request))
            return await _res  # все вернется одновременно потому что токен один

        async def get_eps(_result):
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
                    return
                else:
                    _eps.append({'ep': f'{_msg.family}://{_msg.source[0]}:{_msg.source[1]}'})
                    try:
                        if 'p' in _link and _link['p'].get('sec') and _link['p'].get('port'):
                            _eps.append({'ep': f'coaps://{_msg.source[0]}:{_link["p"]["port"]}'})
                    except Exception:
                        pass
                    return
            else:
                _eps = _payload['eps']
            _result['family'] = _msg.family
            for elem in _eps:
                _url = urlparse(elem['ep'])
                if _url.scheme in ['coap', 'coaps']:
                    _address = _url.netloc.split(":")
                    _result[_url.scheme] = (_address[0], int(_address[1]))

        async def get_name(_result):
            _request = Request()
            _request.type = NON
            _request.code = Code.GET
            _request.uri_path = '/oic/d'
            _request.content_type = 10000
            _request.source = _msg.destination
            _request.family = _msg.family
            _request.scheme = _msg.scheme
            _request.destination = _msg.source
            resp = await self.coap.send_message(_request)
            _payload = resp.decode_payload()
            # result[di]['oic-d'] = json.dumps(_payload)  # debug
            _result['n'] = _payload['n']
            _result['di'] = _payload['di']

        try:
            result = []
            # _address_index = {}
            _list_res = await discover()
            for _msg in _list_res:
                payload = _msg.decode_payload()
                # if not payload:
                #     continue  # todo что то сделать с ошибками

                di = payload['deviceuuid'] if payload else ''
                item = {
                    'net_interface': _msg.destination[0],
                    'di': di
                }
                await get_eps(item)
                await get_name(item)
                result.append(item)

            return result

        except ExtException as e:
            raise Exception(e)
        except Exception as e:
            raise ExtException(parent=e)

    async def find_resource_by_link(self, link):
        self.device.log.debug('find resource by di {0} href {1}'.format(link.di, link.href))

        links = await self.discovery_resource(
            query=dict(di=[link.di], href=[link.href]))
        if isinstance(links, dict):
            for di in links:
                if di == link.di:
                    for ref in links[di].links:
                        if ref == link.href:
                            return links[di].links[ref]
        return None

    pass

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
                        if protocol == AF_INET6:
                            _eps.append({'ep': f'{scheme}://[{_host}]:{port}'})
                        else:
                            _eps.append({'ep': f'{scheme}://{_host}:{port}'})
                else:
                    for host in self.coap.endpoint_layer.unicast_endpoints[scheme][protocol]:
                        for port in self.coap.endpoint_layer.unicast_endpoints[scheme][protocol][host]:
                            if protocol == AF_INET6:
                                _eps.append({'ep': f'{scheme}://[{host}]:{port}'})
                            else:
                                _eps.append({'ep': f'{scheme}://{host}:{port}'})
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

    def _prepare_request(self, operation, to, data=None, *, secure=False, multicast=False, query=None, **kwargs):
        # secure = kwargs.get('secure', False)
        # multicast = kwargs.get('multicast', False)
        scheme = 'coaps' if secure else 'coap'
        family = to['family']

        request = Request()
        request.type = NON
        request.scheme = scheme
        request.multicast = multicast
        request.family = family
        request.source = (to['net_interface'], None)

        if multicast:
            request.destination = (self.coap_discovery[family][0], self.coap_discovery_port)
        else:
            request.destination = to[scheme]

        request.code = self.map_crudn_to_coap_code(operation)
        request.uri_path = to.get('href', '')

        option = Option()
        option.number = defines.OptionRegistry.CONTENT_TYPE.number
        option.value = 10000
        request.add_option(option)

        # request.accept = 10000

        # query = kwargs.get('query')
        if query:
            request.query = query

        if data:
            request.encode_payload(data)
        return request

    def get_endpoint(self, to, *, secure=False, scheme=None):
        request = self._prepare_request('get', to, data=None, secure=secure)
        endpoint = self.coap.endpoint_layer.find_sending_endpoint(request)
        return endpoint

    async def send_message(self, operation, to, data=None, *, secure=False, multicast=False, query=None, **kwargs):
        try:
            request = self._prepare_request(operation, to,
                                            data=data, secure=secure, multicast=multicast, query=query, **kwargs)
            response = await self.coap.send_message(request, **kwargs)

            return response
        except TimeoutError:
            raise ExtTimeoutError(action='request', dump=dict(op=operation, to=to, data=data, kwargs=kwargs)) from None
        except ExtException as err:
            raise ExtException(parent=err,
                               action='{}.request()'.format(self.__class__.__name__),
                               dump=dict(op=operation, to=to, data=data, kwargs=kwargs)) from None
        except Exception as err:
            raise ExtException(parent=err,
                               action='{}.request()'.format(self.__class__.__name__),
                               dump=dict(op=operation, to=to, data=data, kwargs=kwargs)) from err
