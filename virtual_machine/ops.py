# Schemas
ADD = AND = [
    '1110 0000 0000',
    '0001 1100 0000',
    '0000 0000 0111',
    '0000 0001 1111',
    '0000 0010 0000',
]
LD = ST = STI = BR = LEA = LDI = [
    '1110 0000 0000',
    '0001 1111 1111',
]
JMP = [
    '0001 1100 0000',
]
JSR = [
    '1000 0000 0000',
    '0111 1111 1111', 
    '0001 1100 0000', 
]
NOT = [
    '1110 0000 0000',
    '0001 1100 0000',
    '0000 0011 1111'
]
STR = LDR = [
    '1110 0000 0000',
    '0001 1100 0000',
    '0000 0011 1111',
]
TRAP = [
    '0000 1111 1111',
]


SCHEMAS = {
    0: (BR, ("BR", "BRn", "BRp", "BRz", "BRnp", "BRnz", "BRzp", "BRnzp")), # branch
    1: (ADD, ("ADD",)),                                                    # add 
    2: (LD, ("LD",)),                                                      # load
    3: (ST, ("ST",)),                                                      # store
    4: (JSR, ("JSR", "JSRR")),                                             # jump register
    5: (AND, ("AND",)),                                                    # bitwise and
    6: (LDR, ("LDR",)),                                                    # load register
    7: (STR, ("STR",)),                                                    # store register
    8: (None, ()),                                                         # unused
    9: (NOT, ("NOT",)),                                                    # bitwise not
    10: (LDI, ("LDI",)),                                                   # load indirect
    11: (STI, ("STI",)),                                                   # store indirect
    12: (JMP, ("JMP", "RET")),                                             # jump
    13: (None, ()),                                                        # reserved (unused)
    14: (LEA, ("LEA",)),                                                   # load effective address
    15: (TRAP, ("TRAP",)),                                                 # execute trap
}

TRAPS = {
    "GETc": 0x20,
    "OUT": 0x21,
    "PUTs": 0x22,
    "IN": 0x23,
    "PUTsp": 0x24,
    "HALT": 0x25,
}

OPS = {}


class Operation:
    def __init__(self, opcode):
        self.cache = {}
        self.shifts = []
        self.opcode = opcode

        for mask in SCHEMAS[opcode][0]:
            mask = '0000' + mask.replace(' ', '')
            shift = len(mask) - 1 - mask.rfind('1')
            mask = int(mask, 2) >> shift
            self.shifts.append((shift, mask))

    def decode(self, instruction):
        if instruction in self.cache:
            return self.cache[instruction]

        args = []
        for shift, mask in self.shifts:
            args.append((instruction >> shift) & mask)
        self.cache[instruction] = args

        return args

    def encode(self, *args):
        encoded = 0
        for val, (shift, mask) in zip(args, self.shifts):
            if val == None:
                continue
            encoded += (val & mask) << shift
        encoded += self.opcode << 12
        return encoded


for op in SCHEMAS:
    schema, tokens = SCHEMAS[op]
    if schema == None:
        continue
    operation = Operation(op)
    OPS[op] = operation.decode
    for token in tokens:
        OPS[token] = operation.encode


def parse(instruction):
    op = instruction >> 12
    return op, OPS[op](instruction)


def encode(op, *args):
    return OPS[op](*args)

