from urllib.parse import urlparse

class Ep:
    def __init__(self, ep: str):
        self.ep = ep
        self._data = None
        self._address = None
        self._host = None
        self._port = None

    @property
    def _component(self):
        if self._data is None:
            self._data = urlparse(self.ep)
        return self._data

    def _parse_address(self):
        if self._address is None:
            netloc = self._component.netloc.split(':')
            self._host = netloc[0]
            self._port = 0
            if len(netloc) == 2:
                self._port = int(netloc[1])

    @property
    def address(self):
        self._parse_address()
        return self._host, self._port