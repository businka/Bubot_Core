from unittest import TestCase
from Bubot.Core.OcfMessage import OcfRequest, OcfResponse
from Bubot.Core.Coap.coap import Message, Code


class TestOcfMessage(TestCase):
    def setUp(self):
        self.link = None

    def test_retrieve(self):
        sender = {
            'href': '/light',
            'eps': [{'ep': 'coap://127.0.0.1:1111'}]
        }
        receiver = {
            'href': '/oic/res',
            'eps': [{'ep': 'coap://127.0.0.1:2222'}]
        }
        request = OcfRequest(
            to=receiver,
            fr=sender,
            op='retrieve',
            token=1,
            mif=2,
            **dict(
                query={'if': "oic.d"}
            )
        )
        data = None
        answer = OcfResponse.generate_answer(data, request)
        pass

    def test_domx_encode_decode(self):
        data = b'X\x01\xb4\x85\xa0\x02\xacA\x8d\x04N*\xb3oic\x03sec\x04doxmKowned=FALSE"\'\x10\xe2\x06\xe3\x08\x00'
        coap_message = Message.decode(data, ('192.168.1.15', 61689))
        ocf_message = OcfRequest.decode_from_coap(coap_message, False)
        coap_message2, address = ocf_message.encode_to_coap()
        data2 = coap_message2.encode()
        self.assertEqual(data, data2)
        pass
