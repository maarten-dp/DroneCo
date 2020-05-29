from memory import Memory
from enum import Enum
import sys
import select
import tty
import termios
from bitarray.util import ba2int, int2ba


CACHE = {}

def decode(val, *masks):
    if (val, masks) in CACHE:
        return CACHE[(val, masks)]

    args = []
    for mask in masks:
        mask = mask.replace(' ', '')
        shift = len(mask) - 1 - mask.rfind('1')
        mask = int(mask, 2) >> shift
        args.append((val >> shift) & mask)

    CACHE[(val, masks)] = args

    return args
        

# Registers
RR0 = 0
RR1 = 1
RR2 = 2
RR3 = 3
RR4 = 4
RR5 = 5
RR6 = 6
RR7 = 7
RPC = 8
RCOND = 9
RCOUNT = 10

#Opcodes
OP_BR = 0    # branch
OP_ADD = 1   # add 
OP_LD = 2    # load
OP_ST = 3    # store
OP_JSR = 4   # jump register
OP_AND = 5   # bitwise and
OP_LDR = 6   # load register
OP_STR = 7   # store register
OP_RTI = 8   # unused
OP_NOT = 9   # bitwise not
OP_LDI = 10  # load indirect
OP_STI = 11  # store indirect
OP_JMP = 12  # jump
OP_RES = 13  # reserved (unused)
OP_LEA = 14  # load effective address
OP_TRAP = 15 # execute trap


# Flags
FL_POS = 1 << 0
FL_ZRO = 1 << 1
FL_NEG = 1 << 2

# Trap codes
GETC = 0x20
OUT = 0x21
PUTS = 0x22
IN = 0x23
PUTSP = 0x24
HALT = 0x25

# Mapped Registers
MR_KBSR = 0xFE00 # Keyboard status
MR_KBDR = 0xFE02 # Keyboard data


RUNNING = 0
MAX_MEMORY_ADDRESS = 256 * 256
MEMORY = Memory(MAX_MEMORY_ADDRESS)
REGISTERS = Memory(RCOUNT)
OPCODES = {}
TRAPS = {}


def load_image(image):
    # load the origin, which indicates the starting address of the
    # program in memory.
    origin = int.from_bytes(image.read(2), byteorder='big')
    # load actual program instructions in the origin address.
    max_read = MAX_MEMORY_ADDRESS - origin
    MEMORY.frombytes(image.read(max_read), origin)


def mem_read(address):
    address = address & 0xFFFF
    if address == MR_KBDR:
        if check_key():
            MEMORY[MR_KBSR] = 1 << 15
            MEMORY[MR_KBDR] = getchar()
        else:
            MEMORY[MR_KBSR] = 0
    return MEMORY[address]


def mem_write(address, value):
    address = address & 0xFFFF
    MEMORY[address] = value


def check_key():
     # select system call, unix only.
    _, w, _ = select.select([], [sys.stdin], [], 0)
    return len(w)


def getchar():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    if ord(ch) == 3:
        # handle keyboard interrupt
        exit(130)
    return ch


def extend_sign(val, bit_count):
    if val >> (bit_count - 1):
        val = (val | (0xFFF << bit_count)) & 0xFFFF
    return val


def update_flags(val):
    if val == 0:
        REGISTERS[RCOND] = FL_ZRO
    elif val >> 15:
        REGISTERS[RCOND] = FL_NEG
    else:
        REGISTERS[RCOND] = FL_POS


### OPCODES ###
def add(instruction):
    r0, r1, r2, imm5, imm_flag = decode(instruction,
        '1110 0000 0000',
        '0001 1100 0000',
        '0000 0000 0111',
        '0000 0001 1111',
        '0000 0010 0000'
    )

    if imm_flag:
        val = (REGISTERS[r1] + extend_sign(imm5, 5)) & 0xFFFF
    else:
        val = (REGISTERS[r1] + REGISTERS[r2]) & 0xFFFF

    REGISTERS[r0] = val
    update_flags(val)


def load_indirect(instruction):
    r0, pc_offset = decode(instruction,
        '1110 0000 0000',
        '0001 1111 1111',
    )
    pc_offset = extend_sign(pc_offset, 9)
    val = mem_read(Registers[RPC] + pc_offset)
    REGISTERS[r0] = val
    update_flags(val)


def b_and(instruction):
    r0, r1, r2, imm5, imm_flag = decode(instruction,
        '1110 0000 0000',
        '0001 1100 0000',
        '0000 0000 0111',
        '0000 0001 1111',
        '0000 0010 0000'
    )
    if imm_flag:
        val = REGISTERS[r1] & extend_sign(imm5, 5)
    else:
        val = REGISTERS[r1] & REGISTERS[r2]
    REGISTERS[r0] = val
    update_flags(val)


def b_not(instruction):
    r0, r1 = decode(instruction,
        '1110 0000 0000',
        '0001 1100 0000',
    )
    # REGISTERS[r0] = 0xFFF ^ REGISTERS[r1]
    val = ~REGISTERS[r1]
    REGISTERS[r0] = val
    update_flags(val)


def branch(instruction):
    cond_flag, pc_offset = decode(instruction,
        '1110 0000 0000',
        '0001 1111 1111',
    )
    pc_offset = extend_sign(pc_offset, 9)
    if cond_flag & REGISTERS[RCOND]:
        REGISTERS[RPC] =  (REGISTERS[RPC] + pc_offset) & 0xFFFF


def jump(instruction):
    r0, = decode(instruction,
        '0001 1100 0000'
    )
    REGISTERS[RPC] = REGISTERS[r0]


def jump_register(instruction):
    long_flag, long_pc_offset, r1 = decode(instruction,
        '1000 0000 0000',
        '0111 1111 1111',
        '0001 1100 0000'
    )
    REGISTERS[RR7] = REGISTERS[RPC]
    if long_flag:
        long_pc_offset = extend_sign(long_pc_offset, 11)
        REGISTERS[RPC] = (REGISTERS[RPC] + long_pc_offset) & 0xFFFF
    else:
        REGISTERS[RPC] = REGISTERS[r1]


def load(instruction):
    r0, pc_offset = decode(instruction,
        '1110 0000 0000',
        '0001 1111 1111',
    )
    pc_offset = extend_sign(pc_offset, 9)
    val = mem_read(REGISTERS[RPC] + pc_offset)
    REGISTERS[r0] = val
    update_flags(val)


def load_register(instruction):
    r0, r1, offset = decode(instruction,
        '1110 0000 0000',
        '0001 1100 0000',
        '0000 0011 1111',
    )
    offset = extend_sign(offset, 6)
    val = mem_read(REGISTERS[r1] + offset)
    REGISTERS[r0] = val
    update_flags(val)


def load_effective_address(instruction):
    r0, pc_offset = decode(instruction,
        '1110 0000 0000',
        '0001 1111 1111',
    )
    pc_offset = extend_sign(pc_offset, 9)
    val = (REGISTERS[RPC] + pc_offset) & 0xFFFF
    REGISTERS[r0] = val
    update_flags(val)


def store(instruction):
    r0, pc_offset = decode(instruction,
        '1110 0000 0000',
        '0001 1111 1111',
    )
    pc_offset = extend_sign(pc_offset, 9)
    mem_write(REGISTERS[RPC] + pc_offset, REGISTERS[r0])


def store_indirect(instruction):
    r0, pc_offset = decode(instruction,
        '1110 0000 0000',
        '0001 1111 1111',
    )
    pc_offset = extend_sign(pc_offset, 9)
    value = mem_read(REGISTERS[RPC] + pc_offset)
    mem_write(value, REGISTERS[r0])


def store_register(instruction):
    r0, r1, offset = decode(instruction,
        '1110 0000 0000',
        '0001 1100 0000',
        '0000 0011 1111',
    )
    offset = extend_sign(offset, 6)
    mem_write(REGISTERS[r1] + offset, REGISTERS[r0])


def trap(instruction):
    op, = decode(instruction,
        '0000 1111 1111',
    )
    TRAPS[op]()


OPCODES[OP_BR] = branch
OPCODES[OP_ADD] = add
OPCODES[OP_LD] = load
OPCODES[OP_ST] = store
OPCODES[OP_JSR] = jump_register
OPCODES[OP_AND] = b_and
OPCODES[OP_LDR] = load_register
OPCODES[OP_STR] = store_register
OPCODES[OP_RTI] = lambda x: None
OPCODES[OP_NOT] = b_not
OPCODES[OP_LDI] = load_indirect
OPCODES[OP_STI] = store_indirect
OPCODES[OP_JMP] = jump
OPCODES[OP_RES] = lambda x: None
OPCODES[OP_LEA] = load_effective_address
OPCODES[OP_TRAP] = trap


### TRAPS ###
def puts():
    start = REGISTERS[RR0]
    character = MEMORY[start]
    output = ""
    while character:
        # output += chr(character)
        start += 1
        print(chr(character), end='')
        character = MEMORY[start]
    sys.stdout.flush()
    # print(output)


def getc():
    # https://stackoverflow.com/questions/510357/python-read-a-single-character-from-the-user
    REGISTERS[RR0] = ord(getchar())


def t_out():
    print(chr(REGISTERS[RR0]), end='')


def t_in():
    REGISTERS[RR0] = ord(getchar())


def putsp():
    start = REGISTERS[RR0]
    character = MEMORY[start]
    output = ""
    while character:
        ba = bitarray(bin(character)[2:])
        char1 = chr(ba[:8])
        char2 = chr(ba[8:])
        output += char1
        output += char2 if char2 else ''
        start += 1
        character = MEMORY[start]
    print(output)


def halt():
    global RUNNING
    print('Done')
    RUNNING = 0


TRAPS[GETC] = getc
TRAPS[OUT] = t_out
TRAPS[PUTS] = puts
TRAPS[IN] = t_in
TRAPS[PUTSP] = putsp
TRAPS[HALT] = halt

def main():
    global RUNNING
    # import json
    # dump = json.load(open('dump', 'r'))
    REGISTERS[RPC] = 0x3000
    RUNNING = 1
    i = 1
    prev_pc = None
    prev_instr = None
    while RUNNING:
        instr = mem_read(REGISTERS[RPC])
        # print(REGISTERS[RPC])
        REGISTERS[RPC] += 1

        # memsum,ins,pc = dump[i]
        # if ins != instr:
        #     import pdb; pdb.set_trace()
        # if pc != REGISTERS[RPC]:
        #     import pdb; pdb.set_trace()
        # if memsum != sum(MEMORY.mem):
        #     import pdb; pdb.set_trace()

        # prev_instr = instr
        # prev_pc = REGISTERS[RPC]
        # if i == 141:
        #     import pdb; pdb.set_trace()
        # i+=1
        op = instr >> 12
        # print(op)
        OPCODES[op](instr & 0xFFF)


if __name__ == '__main__':
    # load image
    args = sys.argv
    path = args[1]
    with open(path, 'br') as image:
        load_image(image)
    import time
    t1 = time.time()
    main()
    print(time.time() - t1)



