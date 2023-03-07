from unittest import TestCase
from Bubot.Ocf.OcfMessage import OcfRequest, OcfResponse


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
