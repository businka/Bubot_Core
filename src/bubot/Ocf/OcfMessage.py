# from aiocoap import Message, NON, Code
# from bubot.core.Coap.coap import Message, NON, Code
from urllib.parse import urlparse
from uuid import uuid4

import cbor2

from bubot.core.ResourceLink import ResourceLink
from bubot_helpers.ExtException import ExtException, dumps_error
from Bubot_CoAP import defines
from Bubot_CoAP.messages.numbers import NON, Code
from Bubot_CoAP.messages.option import Option
from Bubot_CoAP.messages.request import Request
import bson


class OcfMessage:
    def __init__(self, *, fr=None, to=None, ri=None, cn=None, query=None, **kwargs):
        '''
        :param fr: The URI of the message originator.
        :param to: The URI of the recipient of the message.
        :param ri: The  identifier  that  uniquely  identifies  the message in the originator and the recipient.
        :param cn: Information specific to the operation.
        :param query: ?
        :param kwargs: ?
        '''
        self.data = {}
        self.fr = fr
        self.to = to
        self.ri = ri if ri else str(uuid4())
        self.cn = cn  # Content

        # self.uri_path = kwargs.get('uri_path')
        # self.code = kwargs.get('code')
        # self.query = kwargs.get('query', {})
        # self.token = kwargs.get('token')
        # self.mid = kwargs.get('mid')
        # self.data = kwargs.get('data', {})
        # self.raw_msg = None
        # self.code = kwargs.get('code', NON)
        pass

    def parse_url_to(self):
        return urlparse(self.to)

    @staticmethod
    def init_from_bson(data: bytes):
        _data = bson.decode(data)
        if 'op' in _data:
            return OcfRequest(**_data)
        elif 'rs' in _data:
            return OcfResponse(**_data)
        else:
            raise ExtException(message='Bad message data', dump=_data)

    @staticmethod
    def encode_query(query):
        result = []
        for key in query:
            if not isinstance(query[key], list):
                raise Exception('value query param must be only list')
            for elem in query[key]:
                result.append('{}={}'.format(key, elem))
        return result

    @staticmethod
    def decode_query(query):
        result = {}
        if not query:
            return None
        for elem in query:
            key, value = elem.split('=')
            if key not in query:
                result[key] = []
            result[key].append(value)
            pass
        return result


class OcfRequest(OcfMessage):

    def __init__(self, *, obs=None, op=None, multicast=False, **kwargs):
        super().__init__(**kwargs)
        self.obs = obs
        self.op = op
        # self.multicast = multicast
        # if not self.code or not self.op:
        #     if not self.code and self.op:
        #         self.code = self.map_crudn_to_coap_code(self.op)
        #     else:
        #         raise Exception('не заполнены обязательные параметры')

        # self.observe = None

    def to_dict(self):
        return dict(
            fr=self.fr,
            to=self.to,
            ri=self.ri,
            cn=self.cn,
            op=self.op,
            obs=self.obs
        )

    def generate_error(self, err, *, rs=Code.UNPROCESSABLE_ENTITY, obs=None, **kwargs):
        if not isinstance(err, ExtException):
            err = ExtException(parent=err)
        return OcfResponse(
            to=self.fr,
            fr=self.to,
            ri=self.ri,
            cn=err.to_dict(),
            rs=rs,
            obs=obs if obs else self.obs  # todo не понятно как должно быть
            # uri_query=self.query,
            # token=self.token,
            # mid=self.mid,
        )

    def generate_answer(self, data, *, rs=Code.CONTENT, obs=None, **kwargs):
        return OcfResponse(
            to=self.fr,
            fr=self.to,
            ri=self.ri,
            rs=rs,
            cn=data,
            obs=obs if obs else self.obs  # todo не понятно как должно быть
            # mid=kwargs.get('mid', self.mid),
            # uri_query=self.query,
            # token=self.token,
        )
        # if req.raw_msg:
        #     self.raw_msg = req.raw_msg.copy()
        # self.raw_msg.code = Code.CONTENT

    def encode_to_coap(self):

        # try:
        #     parsed = urllib.parse.urlparse(self.to.get_endpoint(), allow_fragments=False)
        #     address = (parsed.hostname, parsed.port)
        # except KeyError:
        #     address = None
        # return msg2, address

        request = Request()
        request.type = NON
        # request.token = generate_random_token(2)
        request.destination = self.to.get_endpoint_address()
        # request.destination = (sender, 5683)
        request.multicast = self.multicast
        request.source = (self.fr.get_endpoint_address()[0], None)
        request.code = self.code
        request.uri_path = self.to.href

        option = Option()
        option.number = defines.OptionRegistry.CONTENT_TYPE.number
        option.value = 10000
        request.add_option(option)

        option = Option()
        option.number = defines.OptionRegistry.URI_QUERY.number
        option.value = self.encode_query(self.query)  # todo  разобраться что тут надо
        request.add_option(option)
        return request, request.destination

        # params = dict(
        #     mtype=NON,
        #     mid=self.mid,
        #     code=self.code,
        #     token=self.token,
        #     uri_host=self.to.anchor,
        #     uri_query=self.encode_query(self.query),
        #     uri_path=self.to.href[1:].split('/'),
        #     # application/vnd.ocf+cbor
        #     # http://www.iana.org/assignments/core-parameters/core-parameters.xhtml#content-formats
        #     content_format=10000,
        #     accept=10000,
        #     observe=self.obs,
        #     payload=cbor2.dumps(self.cn) if self.cn else b''
        # )
        # msg2 = Message(**params)

    @classmethod
    def decode_from_coap(cls, msg, multicast=False):
        # message = Message.decode(raw_data, remote)
        self = cls(
            fr=ResourceLink.init_from_uri('coap://[{0}]:{1}'.format(msg.remote[0], msg.remote[1])),
            # message.opt.uri_path, message.opt.uri_port))]
            to=ResourceLink.init_from_msg(msg),
            code=int(msg.code),
            op=cls.map_coap_code_to_crudn(msg.code.name),
            obs=msg.opt.observe,
            query=cls.decode_query(msg.opt.uri_query),
            token=msg.token,
            mid=msg.mid,
            multicast=multicast
        )
        self.raw_msg = msg
        self.operation = msg.code.name.lower()

        if msg.payload:
            self.cn = cbor2.loads(msg.payload)

        return self

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
            'retrieve': 1,
            'update': 2,
            'delete': 4,
        }
        return map_crudn_to_coap[operation.lower()]


class OcfResponse(OcfMessage):
    def __init__(self, *, rs=None, obs=None, **kwargs):
        super().__init__(**kwargs)
        # self.error = self.is_successful(kwargs['rs'].)
        self.rs = rs  # Response Code RFC 7252
        self.obs = obs  # Observe
        # self.observe = kwargs.get('observe', None)

        # +------+------------------------------+-----------+
        # | Code | Description                  | Reference |
        # +------+------------------------------+-----------+
        # | 2.01 | Created                      | [RFC7252] |
        # | 2.02 | Deleted                      | [RFC7252] |
        # | 2.03 | Valid                        | [RFC7252] |
        # | 2.04 | Changed                      | [RFC7252] |
        # | 2.05 | Content                      | [RFC7252] |
        # | 4.00 | Bad Request                  | [RFC7252] |
        # | 4.01 | Unauthorized                 | [RFC7252] |
        # | 4.02 | Bad Option                   | [RFC7252] |
        # | 4.03 | Forbidden                    | [RFC7252] |
        # | 4.04 | Not Found                    | [RFC7252] |
        # | 4.05 | Method Not Allowed           | [RFC7252] |
        # | 4.06 | Not Acceptable               | [RFC7252] |
        # | 4.12 | Precondition Failed          | [RFC7252] |
        # | 4.13 | Request Entity Too Large     | [RFC7252] |
        # | 4.15 | Unsupported Content - Format | [RFC7252] |
        # | 5.00 | Internal Server Error        | [RFC7252] |
        # | 5.01 | Not Implemented              | [RFC7252] |
        # | 5.02 | Bad Gateway                  | [RFC7252] |
        # | 5.03 | Service Unavailable          | [RFC7252] |
        # | 5.04 | Gateway ExtTimeoutError      | [RFC7252] |
        # | 5.05 | Proxying Not Supported       | [RFC7252] |
        # +------+------------------------------+-----------+

    def to_dict(self):
        return dict(
            fr=self.fr,
            to=self.to,
            ri=self.ri,
            cn=self.cn,
            rs=self.rs,
            obs=self.obs
        )

    def is_successful(self):
        """True if the code is in the successful subrange of the response code range"""
        return True if (64 <= self.rs < 96) else False

    def encode_to_coap(self):
        parsed = urlparse(self.fr.get_endpoint(), allow_fragments=False)
        msg2 = Message(
            mtype=NON,
            mid=self.mid,
            code=self.rs,
            observe=self.obs,
            payload=cbor2.dumps(self.cn) if self.cn else b'',
            token=self.token,
            uri_query=self.encode_query(self.query),
            uri_host=self.to.anchor,
            uri_path=self.to.href[1:].split('/'),
            content_format=10000,
            accept=10000
            # iotivity_addresses=b'\xc0'
        )
        # message = self.raw_msg
        # message.code = self.code
        # message.payload = cbor2.dumps(self.data) if self.data else b''
        # message.mtype = NON
        return msg2, (parsed.hostname, parsed.port)

    @classmethod
    def decode_from_coap(cls, msg, multicast=False):
        # message = Message.decode(raw_data, remote)
        self = cls(
            code=int(msg.code),
            rs=msg.code.name.lower(),
            token=msg.token,
            mid=msg.mid,
            query=cls.decode_query(msg.opt.uri_query),
            obs=msg.opt.observe,
            multicast=multicast,
            to=ResourceLink.init_from_msg(msg)
        )
        self.raw_msg = msg
        self.operation = msg.code.name.lower()
        if msg.payload:
            self.cn = cbor2.loads(msg.payload)
        if msg.opt.uri_query:
            for elem in msg.opt.uri_query:
                key, value = elem.split('=')
                if key not in self.uri_query:
                    self.uri_query[key] = []
                self.uri_query[key].append(value)
                pass
        return self

    # def to_dict(self):
    #     return dict(
    #         code=self.code,
    #         token=self.token,
    #         mid=self.mid,
    #         obs=self.obs,
    #         fr=self.fr.data if self.fr else None,
    #         to=self.to.data if self.to else None,
    #         cn=self.cn
    #     )
    #
    # def __str__(self):
    #     return '{code} {value}'.format(value=str(self.cn))
