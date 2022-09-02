class OcfMessage:
    def __init__(self):
        self.source = None
        self.dest = None
        self.data = None
        self.raw_msg = None
        self.family = None
        self.scheme = None
        self.path = None
        self.query = None

    @classmethod
    def init_from_CoapMessage(cls, msg):
        self = cls()
        self.data = msg.decode_data()
        self.family = self.family
        self.scheme = self.scheme
