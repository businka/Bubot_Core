import unittest
import os
from bubot.JsonSchema4 import JsonSchema4
from bubot.Helper import Helper


class TestJsonSchema(unittest.TestCase):
    def test_init_from_file(self):
        folder = os.path.dirname(__file__)
        name = 'oic.wk.d-schema.json'
        schema = JsonSchema4.load_from_file(name, folder=folder + '\schemas')
        print(schema)
        pass

    def test_init_from_rt(self):
        folder = os.path.dirname(__file__)
        name = 'oic.wk.res'
        schema = JsonSchema4().load_from_rt([name])
        print(schema)
        pass

    def test_load_for_resource(self):
        folder = os.path.dirname(__file__)
        rt = [
            "oic.r.light.brightness",
            "oic.r.colour.rgb",
            "oic.r.switch.binary"
        ]
        cache = {}
        handler = JsonSchema4(folder=folder + '\schemas', cache=cache)
        _schema = handler.load_from_rt(rt)
        pass
