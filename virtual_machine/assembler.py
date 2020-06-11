import array
import sys
from copy import deepcopy
from .ops import encode, TRAPS, OPS


REG = {
    "R0": 0,
    "R1": 1,
    "R2": 2,
    "R3": 3,
    "R4": 4,
    "R5": 5,
    "R6": 6,
    "R7": 7,
}

BASE_MAPPING = {
    '#': 10,
    'x': 16,
    'X': 16,
    'b': 2,
    'B': 2
}


def raise_parse_error():
    import pdb; pdb.set_trace()


def is_int(arg):
    try:
        int(arg)
        return True
    except ValueError:
        return False


class Addressable:
    def __init__(self, address, labels, op):
        self.address = address
        self.labels = labels
        self.op = op

    def get_next_address(self):
        return self.address + 1

    def get_value(self, value):
        if value is None:
            return value
        if value in REG:
            return REG[value]
        elif value in self.labels:
            return self.labels[value].address
        elif value[0] in BASE_MAPPING:
            return int(value[1:], BASE_MAPPING[value[0]])
        elif is_int(value):
            return int(value)
        raise_parse_error()


class OP(Addressable):
    def to_bytes(self):
        print(self.address, self.op)
        if self.op[0] == 'RET':
            return [0xC1C0]
        op, args = self.op
        args = args.replace(' ', '').split(',')

        if op.startswith('BR'):
            n = ('n' in op) << 2
            z = ('z' in op) << 1
            p = ('p' in op)
            args.insert(0, str(n + z + p))
            if args[1] in self.labels:
                args[1] = str((self.labels[args[1]].address - (self.address + 1)) & 0xFFF)
        if op in ('AND', 'ADD'):
            imm = str(int(args[2] not in REG))
            if imm == '1':
                args.insert(-1, None)
            else:
                args.append(None)
            args.append(imm)
        if op in ('LD', 'LEA', 'LDI', 'ST', 'STI'):
            args[1] = str((self.labels[args[1]].address - (self.address + 1)) & 0xFFF)
        if 'JSR' in op:
            long_offset = '0'
            if args[0] in self.labels:
                long_offset = '1'
                args[0] = str((self.labels[args[0]].address - (self.address + 1)) & 0xFFF)
            args.insert(0,long_offset)
            args.append(None)
        if 'NOT' in op:
            args.append(str(0b111111))

        return [encode(op, *[self.get_value(a) for a in args])]


class Variable(Addressable):
    def __init__(self, address, labels, op):
        super().__init__(address, labels, op)
        stripped = ' '.join(self.op[1].split())
        var_type, var = stripped.split(' ', 1)
        if var_type == ".STRINGZ":
            var = var.replace('"', '')
            var = var.replace('\\t', '\t')
            var = var.replace('\\n', '\n')
            var = var.replace("\\e", '\x1b')
            var = [ord(c) for c in var] + [0]
        if var_type == '.FILL':
            var = [self.get_value(var)]
        self.var_type = var_type
        self.value = var

    def get_next_address(self):
        return self.address + len(self.value)

    def to_bytes(self):
        print(self.address, self.op)
        return self.value


class Trap(Addressable):
    def to_bytes(self):
        return [encode('TRAP', TRAPS[self.op[0]])]


def sanitize_line(line):
    if ';' in line:
        line = line[:line.index(';')]
    line = line.strip()
    if not line:
        return None
    return line.split(' ', 1)


def prepare_data(orig, statements):

    byte_data = [orig]
    for statement in statements:
        byte_data.extend(statement.to_bytes())

    data = array.array('H', byte_data)
    data.byteswap()
    return data


def write(data):
    with open('out.sym', 'wb') as fh:
        fh.write(data.tobytes())


def process_lines(lines):
    orig = lines.pop(0)
    while orig.startswith(';') or not orig.strip():
        orig = lines.pop(0)

    if not orig.startswith('.ORIG x'):
        raise_parse_error(0, orig, ".ORIG <address>")
    _, val = sanitize_line(orig)
    orig = address = int(val[1:], 16)

    labels = deepcopy(REG)
    statements = []

    label = None
    for line in lines:
        op = sanitize_line(line)

        if not op:
            continue
        if op[0] == '.END':
            break

        if op[0] in OPS:
            statement = OP(address, labels, op)
            if label:
                labels[label] = statement
                label = None
        elif op[0] in TRAPS:
            statement = Trap(address, labels, op)
        elif not op[0].startswith('.'):
            if len(op) == 1:
                label = op[0]
                continue
            statement = Variable(address, labels, op)
            labels[statement.op[0]] = statement
        address = statement.get_next_address()
        statements.append(statement)
    return orig, statements


if __name__ == '__main__':
    path = sys.argv[1]
    with open(path, 'r') as fh:
        lines = fh.readlines()
    data = prepare_date(*process_lines(lines))
    write(data)
