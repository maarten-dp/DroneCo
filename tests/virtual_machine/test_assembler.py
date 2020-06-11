import os
from virtual_machine import assembler as a


ROOT_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.abspath(os.path.join(ROOT_DIR, os.path.pardir, 'data'))


def test_it_can_assemble_a_file():
    path = os.path.join(DATA_DIR, "rogue.asm")
    expected = open(os.path.join(DATA_DIR, "rogue.obj"), 'br').read()

    with open(path, 'r') as fh:
        lines = fh.readlines()
    data = a.prepare_data(*a.process_lines(lines)).tobytes()

    assert len(expected) == len(data)
    for idx, (b1, b2) in enumerate(zip(expected, data)):
        assert b1 == b2, f"{idx}: {b1} != {b2}"



