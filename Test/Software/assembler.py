# ============================================================================
# File: Test/Software/assembler.py
# Description: Assemble a 4x4 matmul and check it on the GPU.
#
# This file is a standalone cocotb run. It is not registered with test_runner.
# Run it with the MSYS2 mingw64 Python, from this directory:
#
#     python assembler.py
# ============================================================================

import sys
import time
from pathlib import Path

import cocotb
import numpy as np
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

SOFTWARE_DIR = Path(__file__).resolve().parent
TEST_DIR = SOFTWARE_DIR.parent
sys.path.insert(0, str(TEST_DIR))
sys.path.insert(0, str(TEST_DIR / "Utils"))

from golden_models import matrix_a, matrix_b, matrix_c

# Opcodes from Source/Includes/defines.vh
OP_ADD = 0x1
OP_SUB = 0x2
OP_MUL = 0x3
OP_LDR = 0x8
OP_STR = 0x9
OP_BR = 0xC
OP_HALT = 0xF

R0, R1, R2, R3, R4, R5, R6, R7 = range(8)

# Data image. The emitters below bake these addresses into ADD/MUL sequences.
N = 4
A_BASE = 16
B_BASE = 32
C_BASE = 48
CLOCK_NS = 10
CYCLE_LIMIT = 8000


def encode_inst(opcode, rdst=0, rsrc1=0, rsrc2=0):
    """Pack one 16-bit instruction: opcode | rdst | rsrc1 | rsrc2."""
    return (
        ((opcode & 0xF) << 12)
        | ((rdst & 0x7) << 9)
        | ((rsrc1 & 0x7) << 6)
        | ((rsrc2 & 0x7) << 3)
    )


class Program:
    """Instruction list with labels for the branch targets stored in data memory."""

    def __init__(self):
        self.words = []
        self.labels = {}

    def label(self, name):
        self.labels[name] = len(self.words)

    def emit(self, opcode, rd=0, rs1=0, rs2=0):
        self.words.append(encode_inst(opcode, rd, rs1, rs2))

    def size(self):
        if len(self.words) > 256:
            raise AssertionError(f"program is {len(self.words)} words, imem holds 256")
        return len(self.words)


def emit_bases_from_row(prog):
    """R7 is the row and R1 is 1. Leave &A[row] in R4 and &C[row] in R3.

    A is row-major at address 16, so the row starts at 16 + row * 4.
    C is row-major at address 48.
    """
    prog.emit(OP_ADD, rd=R6, rs1=R1, rs2=R1)  # 2
    prog.emit(OP_ADD, rd=R6, rs1=R6, rs2=R6)  # 4
    prog.emit(OP_MUL, rd=R5, rs1=R7, rs2=R6)  # row * 4
    prog.emit(OP_MUL, rd=R2, rs1=R6, rs2=R6)  # 16
    prog.emit(OP_ADD, rd=R4, rs1=R2, rs2=R5)  # &A[row]
    prog.emit(OP_ADD, rd=R6, rs1=R2, rs2=R2)  # 32
    prog.emit(OP_ADD, rd=R3, rs1=R6, rs2=R2)  # 48
    prog.emit(OP_ADD, rd=R3, rs1=R3, rs2=R5)  # &C[row]


def emit_row_dot(prog):
    """Write C[row] from A[row] and B. R4 is &A[row], R3 is &C[row], R1 is 1.

    B is stored column-major at address 32, so column j is the contiguous
    run 32 + j * 4. Every lane executes this same stream; lanes differ only
    in the row pointer already sitting in R4 and R3.
    """
    for column in range(N):
        prog.emit(OP_SUB, rd=R2, rs1=R1, rs2=R1)  # acc = 0
        prog.emit(OP_SUB, rd=R0, rs1=R1, rs2=R1)  # 0
        prog.emit(OP_ADD, rd=R5, rs1=R4, rs2=R0)  # A walk = &A[row]

        # B column pointer = 32 + column * 4
        prog.emit(OP_ADD, rd=R7, rs1=R1, rs2=R1)  # 2
        prog.emit(OP_ADD, rd=R7, rs1=R7, rs2=R7)  # 4
        prog.emit(OP_ADD, rd=R7, rs1=R7, rs2=R7)  # 8
        prog.emit(OP_ADD, rd=R7, rs1=R7, rs2=R7)  # 16
        prog.emit(OP_ADD, rd=R7, rs1=R7, rs2=R7)  # 32
        prog.emit(OP_ADD, rd=R0, rs1=R1, rs2=R1)  # 2
        prog.emit(OP_ADD, rd=R0, rs1=R0, rs2=R0)  # 4
        for _ in range(column):
            prog.emit(OP_ADD, rd=R7, rs1=R7, rs2=R0)

        for _ in range(N):
            prog.emit(OP_LDR, rd=R6, rs1=R5)  # a = A[row][k]
            prog.emit(OP_ADD, rd=R5, rs1=R5, rs2=R1)
            prog.emit(OP_LDR, rd=R0, rs1=R7)  # b = B[k][column]
            prog.emit(OP_MUL, rd=R0, rs1=R6, rs2=R0)
            prog.emit(OP_ADD, rd=R2, rs1=R2, rs2=R0)  # acc += a * b
            prog.emit(OP_ADD, rd=R7, rs1=R7, rs2=R1)

        prog.emit(OP_SUB, rd=R0, rs1=R1, rs2=R1)  # 0
        prog.emit(OP_ADD, rd=R6, rs1=R3, rs2=R0)  # &C[row]
        for _ in range(column):
            prog.emit(OP_ADD, rd=R6, rs1=R6, rs2=R1)
        prog.emit(OP_STR, rs1=R6, rs2=R2)  # C[row][column] = acc


def build_parallel():
    """One block, four lanes. R7 is the row, so each lane writes one row of C."""
    prog = Program()
    prog.emit(OP_LDR, rd=R1, rs1=R0)  # R1 = mem[0] = 1. R0 is 0 after reset.
    emit_bases_from_row(prog)
    emit_row_dot(prog)
    prog.emit(OP_HALT)

    dmem = np.zeros(256, dtype=np.uint8)
    dmem[0] = 1
    _place_matrices(dmem)
    return prog.words, dmem


def build_serial():
    """Lane 0 walks all four rows. Lanes 1..3 branch to HALT on the first BR.

    There is no conditional branch, so the row loop loads its next PC from a
    table. mem[8..10] return to the loop and mem[11] goes to HALT once the
    row counter becomes 4. The counter itself lives at mem[5].
    """
    prog = Program()
    prog.emit(OP_LDR, rd=R6, rs1=R7)  # target = mem[lane]
    prog.emit(OP_BR, rs1=R6)
    prog.label("setup")
    # Lane 0 arrives here with R6 == 2, because mem[0] holds this address.
    prog.emit(OP_ADD, rd=R4, rs1=R6, rs2=R6)  # 4
    prog.emit(OP_LDR, rd=R1, rs1=R4)  # R1 = mem[4] = 1
    prog.label("loop")
    _emit_load_row(prog)
    emit_bases_from_row(prog)
    emit_row_dot(prog)
    _emit_next_row(prog)
    prog.label("halt")
    prog.emit(OP_HALT)

    if prog.labels["setup"] != 2:
        raise AssertionError("serial setup must sit at PC 2 so R6 + R6 builds the constant 4")
    prog.size()

    dmem = np.zeros(256, dtype=np.uint8)
    dmem[0] = prog.labels["setup"]
    dmem[1] = prog.labels["halt"]
    dmem[2] = prog.labels["halt"]
    dmem[3] = prog.labels["halt"]
    dmem[4] = 1
    dmem[8] = prog.labels["loop"]
    dmem[9] = prog.labels["loop"]
    dmem[10] = prog.labels["loop"]
    dmem[11] = prog.labels["halt"]
    _place_matrices(dmem)
    return prog.words, dmem


def _emit_load_row(prog):
    """Load the row counter at mem[5] into R7. R1 is 1."""
    prog.emit(OP_ADD, rd=R6, rs1=R1, rs2=R1)  # 2
    prog.emit(OP_ADD, rd=R6, rs1=R6, rs2=R6)  # 4
    prog.emit(OP_ADD, rd=R6, rs1=R6, rs2=R1)  # 5
    prog.emit(OP_LDR, rd=R7, rs1=R6)


def _emit_next_row(prog):
    """Add one to mem[5] and branch through the table at mem[7 + row]."""
    prog.emit(OP_ADD, rd=R6, rs1=R1, rs2=R1)  # 2
    prog.emit(OP_ADD, rd=R6, rs1=R6, rs2=R6)  # 4
    prog.emit(OP_ADD, rd=R6, rs1=R6, rs2=R1)  # 5
    prog.emit(OP_LDR, rd=R7, rs1=R6)
    prog.emit(OP_ADD, rd=R7, rs1=R7, rs2=R1)
    prog.emit(OP_STR, rs1=R6, rs2=R7)

    prog.emit(OP_ADD, rd=R2, rs1=R1, rs2=R1)  # 2
    prog.emit(OP_ADD, rd=R2, rs1=R2, rs2=R2)  # 4
    prog.emit(OP_ADD, rd=R0, rs1=R2, rs2=R2)  # 8
    prog.emit(OP_SUB, rd=R0, rs1=R0, rs2=R1)  # 7
    prog.emit(OP_ADD, rd=R0, rs1=R0, rs2=R7)  # 7 + new row
    prog.emit(OP_LDR, rd=R0, rs1=R0)
    prog.emit(OP_BR, rs1=R0)


def _place_matrices(dmem):
    dmem[A_BASE:A_BASE + N * N] = matrix_a().flatten(order="C")
    # Column-major, so B[k][j] lives at B_BASE + j * N + k.
    dmem[B_BASE:B_BASE + N * N] = matrix_b().flatten(order="F")


def drive_idle(dut):
    dut.reset.value = 1
    dut.launch.value = 0
    dut.block_count.value = 0
    dut.host_inst_we.value = 0
    dut.host_inst_addr.value = 0
    dut.host_inst_data.value = 0
    dut.host_mem_we.value = 0
    dut.host_mem_re.value = 0
    dut.host_mem_addr.value = 0
    dut.host_mem_wdata.value = 0


async def write_inst(dut, addr, inst):
    await FallingEdge(dut.clk)
    dut.host_inst_we.value = 1
    dut.host_inst_addr.value = addr
    dut.host_inst_data.value = int(inst)
    await RisingEdge(dut.clk)
    dut.host_inst_we.value = 0


async def write_mem(dut, addr, data):
    await FallingEdge(dut.clk)
    dut.host_mem_we.value = 1
    dut.host_mem_re.value = 0
    dut.host_mem_addr.value = addr
    dut.host_mem_wdata.value = int(data)
    await RisingEdge(dut.clk)
    dut.host_mem_we.value = 0


async def read_mem(dut, addr):
    dut.host_mem_we.value = 0
    dut.host_mem_re.value = 1
    dut.host_mem_addr.value = addr
    await Timer(1, unit="ns")
    value = int(dut.host_mem_rdata.value)
    dut.host_mem_re.value = 0
    return value


async def run_image(dut, imem, dmem):
    """Reset, preload, launch one block, and return (cycles, matrix C)."""
    dut.reset.value = 1
    dut.launch.value = 0
    dut.host_inst_we.value = 0
    dut.host_mem_we.value = 0
    dut.host_mem_re.value = 0
    await RisingEdge(dut.clk)
    dut.reset.value = 0
    await Timer(1, unit="ns")

    for addr, inst in enumerate(imem):
        await write_inst(dut, addr, inst)
    for addr in range(A_BASE, C_BASE + N * N):
        await write_mem(dut, addr, dmem[addr])
    for addr in range(12):
        await write_mem(dut, addr, dmem[addr])

    await FallingEdge(dut.clk)
    dut.launch.value = 1
    dut.block_count.value = 1
    await RisingEdge(dut.clk)
    dut.launch.value = 0
    cycles = 1

    for _ in range(CYCLE_LIMIT):
        if int(dut.done.value) == 1 and int(dut.busy.value) == 0:
            break
        await RisingEdge(dut.clk)
        cycles += 1
    else:
        raise AssertionError("GPU did not finish the matmul")

    values = [await read_mem(dut, C_BASE + index) for index in range(N * N)]
    return cycles, np.array(values, dtype=np.uint8).reshape(N, N)


def _show(title, matrix):
    print(f"{title}\n{np.array2string(matrix)}")


@cocotb.test()
async def test_gpu_matmul(dut):
    """Check a 4x4 matmul on four lanes, then the same multiply on one lane."""
    expected = matrix_c()
    wide = matrix_a().astype(np.uint16) @ matrix_b().astype(np.uint16)
    assert int(wide.max()) <= 255, "sample overflows uint8, so it no longer matches the real product"

    drive_idle(dut)
    cocotb.start_soon(Clock(dut.clk, CLOCK_NS, unit="ns").start())

    parallel_imem, parallel_dmem = build_parallel()
    serial_imem, serial_dmem = build_serial()
    parallel_cycles, parallel_c = await run_image(dut, parallel_imem, parallel_dmem)
    serial_cycles, serial_c = await run_image(dut, serial_imem, serial_dmem)

    numpy_started = time.perf_counter()
    timed = matrix_c()
    numpy_us = (time.perf_counter() - numpy_started) * 1e6

    _show("A", matrix_a())
    _show("B", matrix_b())
    _show("NumPy C", expected)
    _show("GPU C, four lanes", parallel_c)
    _show("GPU C, one lane", serial_c)
    print(
        f"Parallel: {parallel_cycles} cycles, {parallel_cycles * CLOCK_NS} ns simulated, "
        f"{len(parallel_imem)} instructions"
    )
    print(
        f"Serial:   {serial_cycles} cycles, {serial_cycles * CLOCK_NS} ns simulated, "
        f"{len(serial_imem)} instructions, repeated for 4 rows"
    )
    print(f"Speedup (serial cycles / parallel cycles): {serial_cycles / parallel_cycles:.2f}x")
    print(f"NumPy matrix_c(): {numpy_us:.1f} us host wall-clock")

    assert np.array_equal(timed, expected)
    assert np.array_equal(parallel_c, expected), "four-lane GPU result differs from NumPy"
    assert np.array_equal(serial_c, expected), "one-lane GPU result differs from NumPy"


def main():
    from cocotb_tools.runner import get_runner
    import test_config as config

    runner = get_runner(config.DEFAULT_SIMULATOR)
    build_dir = config.SIM_BUILD_ROOT / "matmul"
    runner.build(
        sources=config.RTL_SOURCES["gpu"],
        hdl_toplevel="gpu",
        includes=config.INCLUDE_PATHS,
        always=True,
        build_dir=build_dir,
    )
    runner.test(
        hdl_toplevel="gpu",
        test_module="assembler",
        test_dir=SOFTWARE_DIR,
        waves=True,
        results_xml=str(build_dir / "matmul_results.xml"),
    )


if __name__ == "__main__":
    main()
