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
    0: BR,      # branch
    1: ADD,     # add 
    2: LD,      # load
    3: ST,      # store
    4: JSR,     # jump register
    5: AND,     # bitwise and
    6: LDR,     # load register
    7: STR,     # store register
    8: None,    # unused
    9: NOT,     # bitwise not
    10: LDI,    # load indirect
    11: STI,    # store indirect
    12: JMP,    # jump
    13: None,   # reserved (unused)
    14: LEA,    # load effective address
    15: TRAP,   # execute trap
}

OPS = {}


class Operation:
    def __init__(self, opcode):
        self.cache = {}
        self.shifts = []
        self.opcode = opcode

        for mask in SCHEMAS[opcode]:
            mask = '0000' + mask.replace(' ', '')
            shift = len(mask) - 1 - mask.rfind('1')
            mask = int(mask, 2) >> shift
            self.shifts.append((shift, mask))

    @classmethod
    def parse(self, instruction):
        op = instruction >> 12
        return op, OPS[op](instruction)

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
        return encoded


for op in SCHEMAS:
    if SCHEMAS[op] == None:
        continue
    OPS[op] = Operation(op).decode

