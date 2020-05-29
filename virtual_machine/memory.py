class OutOfBoundsException(Exception): pass


class Memory(list):
    def __init__(self, size):
        super().__init__([0] * size)
        self.set = super().__setitem__
        self.get = super().__getitem__

    def __setitem__(self, index, value):
        index = index & 0xFFFF
        self.set(index, value)

    def __getitem__(self, index):
        index = index & 0xFFFF
        return self.get(index)

    def frombytes(self, bytestring, origin):
        pairs = zip(bytestring[::2], bytestring[1::2])
        for address, (b1, b2) in enumerate(pairs, origin):
            self[address] = (b1 << 8 | b2)
