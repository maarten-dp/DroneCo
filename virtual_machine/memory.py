import array

class OutOfBoundsException(Exception): pass


class Memory:
    def __init__(self, size):
        # self.mem = array.array('H', [0] * size)
        self.mem = [0] * size

    def __setitem__(self, key, value):
        self.mem[key] = value & 0xFFFF

    def __getitem__(self, key):
        return self.mem[key]

    def frombytes(self, bytestring, origin):
        pairs = zip(bytestring[::2], bytestring[1::2])
        for address, (b1, b2) in enumerate(pairs, origin):
            self[address] = (b1 << 8 | b2)
