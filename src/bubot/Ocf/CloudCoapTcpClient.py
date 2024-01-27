import asyncio
from asyncio import TimeoutError
from socket import AF_INET
from bubot_helpers.ArrayHelper import ArrayHelper

from Bubot_CoAP import defines
from Bubot_CoAP.messages.numbers import NON
from Bubot_CoAP.messages.option import Option
from Bubot_CoAP.messages.request import Request
from Bubot_CoAP.messages.response import Response
from bubot.Ocf.const import OcfCoapCode
from urllib.parse import urlparse
from bubot_helpers.ExtException import ExtException, ExtTimeoutError, KeyNotFound


class CloudCoapTcpClient:
    def __init__(self, device, coap):
        self.device = device
        self.coap = coap
        self.endpoint = None
        self.destination = None

    async def connect(self):
        if self.endpoint and not self.endpoint.is_closing():
            return
        cloud_cis = self.device.get_param('/CoAPCloudConfResURI', 'cis', None)
        cloud_sid = self.device.get_param('/CoAPCloudConfResURI', 'sid', None)
        cloud_access_token = self.device.get_cloud_access_token()
        if cloud_cis and (cloud_sid or cloud_access_token):
            try:
                self.device.log.info(f'Connected to cloud {cloud_cis}')
                self.endpoint = await self.coap.start_client(cloud_cis)
                self.device.set_param('/CoAPCloudConfResURI', 'clec', '')
            except Exception as err:
                self.device.set_param('/CoAPCloudConfResURI', 'clec', str(err))
                self.device.log.error(str(err))
                return
            try:
                self.destination = urlparse(cloud_cis)
                sid = self.device.get_param('/CoAPCloudConfResURI', 'sid', None)
                if sid:
                    await self.cloud_register(sid)
                await self.cloud_login()
                if sid:
                    await self.cloud_publish_resources()
                    self.device.update_param('/CoAPCloudConfResURI', 'sid', '')
            except Exception as err:
                self.device.set_param('/CoAPCloudConfResURI', 'clec', str(err))
                self.endpoint.close()
                self.device.log.error(str(err))
                return

    async def disconnect(self):
        if self.endpoint:
            self.endpoint.close()

    async def cloud_register(self, sid):
        auth_provider = self.device.get_param('/CoAPCloudConfResURI', 'apn', None)
        try:
            self.device.log.info(f'register access token {sid}')
            res = await self.send_message(OcfCoapCode.UPDATE, '/oic/sec/account', {
                "authprovider": auth_provider,
                "accesstoken": sid,
                "di": self.device.di
            }, timeout=0)
            result = res.decode_payload()
            if not result['accesstoken']:
                raise NotImplementedError()
            cred, creds, cred_index = self.device.get_owner_cred()
            cred['privatedata']['cloud_access_token'] = result['accesstoken']
            self.device.update_param('/CoAPCloudConfResURI', 'sid', '')
            self.device.update_param('/CoAPCloudConfResURI', 'clec', '')
            self.device.update_param('/oic/sec/cred', 'creds', creds)

            self.device.save_config()
        except Exception as err:
            self.device.set_param('/CoAPCloudConfResURI', 'clec', str(err))
            raise err
        return result

    async def cloud_login(self):
        try:
            owner_uid = self.device.get_param('/oic/sec/cred', 'rowneruuid', None)
            cloud_access_token = self.device.get_cloud_access_token()
            res = await self.send_message(OcfCoapCode.UPDATE, '/oic/sec/session', {
                "uid": owner_uid,
                "di": self.device.di,
                "accesstoken": cloud_access_token,
                "login": True,
            }, timeout=0)
            return res

        except Exception as err:
            raise ExtException(parent=err)

    async def cloud_logout(self):
        user_uid = self.device.get_param('/oic/sec/session', 'uid', None)
        access_token = self.device.get_param('/oic/sec/session', 'accesstoken', None)
        res = await self.send_message(OcfCoapCode.UPDATE, '/oic/sec/session', {
            "uid": user_uid,
            "di": self.device.di,
            "accesstoken": access_token,
            "login": True,
        })
        return res

    async def cloud_publish_resources(self):
        links = []
        for href, res in self.device.res.items():
            if res.observable:
                links.append(res.get_link())
        res = await self.send_message(OcfCoapCode.UPDATE, '/oic/rd', {
            "di": self.device.di,
            "ttl": 0,
            "links": links
        })
        return res

    def _prepare_request(self, operation: OcfCoapCode, href, data=None, *, query=None, **kwargs):
        try:
            # secure = kwargs.get('secure', False)
            # multicast = kwargs.get('multicast', False)
            # if secure:
            #     scheme = 'coaps'
            #     family = AF_INET6
            # else:
            scheme = self.destination.scheme
            family = AF_INET  # todo detect from address

            request = Request()
            request.type = NON
            request.scheme = scheme
            request.family = family
            request.destination = self.destination.hostname, self.destination.port
            # ep = to.get_endpoint_by_scheme(scheme)
            # try:
            #     request.source = (ep['net_interface'], None)
            #     request.destination = get_address_from_url(ep['ep'])
            # except (KeyError, TypeError) as err:
            #     raise KeyNotFound(message='Endpoint param not defined', detail=err)

            request.code = operation.value
            request.uri_path = href

            request.add_option(Option(defines.OptionRegistry.CONTENT_TYPE, 10000))

            # request.accept = 10000

            if query:
                request.query = query

            if data:
                request.encode_payload(data)
            return request
        except Exception as err:
            raise ExtException(parent=err)

    async def _send_message(self, request, **kwargs):
        try:
            response: Response = await self.coap.send_message(request, endpoint=self.endpoint, **kwargs)
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

    async def send_message(self, operation: OcfCoapCode, href: str, data=None, **kwargs):
        if not self.endpoint:
            raise ExtException(message='coap server not initialized')
        try:
            request = self._prepare_request(operation, href, data=data, **kwargs)

            return await self._send_message(request, **kwargs)
        except Exception as err:
            raise ExtException(parent=err,
                               action='{}.request()'.format(self.__class__.__name__),
                               dump=dict(op=operation, data=data, kwargs=kwargs))

    async def connection_made(self, protocol):
        pass

    async def connection_lost(self, protocol, exc):
        self.device.log.info(f'Cloud disconnected ')
        pass
