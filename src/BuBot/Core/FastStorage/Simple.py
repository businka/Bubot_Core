class SimpleFastStorage:
    def __init__(self):
        self.storage = {}

    async def set(self, key, value, **kwargs):
        self.storage[key] = value

    async def get(self, key, **kwargs):
        return self.storage[key]
