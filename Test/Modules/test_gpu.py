# ============================================================================
# File: Test/Modules/test_gpu.py
# Description: Cocotb test cases for the four-core Tiny-GPU top.
# ============================================================================

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

OP_ADD  = 0x1
OP_LDR  = 0x8
OP_STR  = 0x9
OP_HALT = 0xF


def encode_inst(opcode, rdst=0, rsrc1=0, rsrc2=0):
    """Pack one 16-bit instruction: opcode | rdst | rsrc1 | rsrc2"""
    return ((opcode & 0xF) << 12) | ((rdst & 0x7) << 9) | ((rsrc1 & 0x7) << 6) | ((rsrc2 & 0x7) << 3)


async def start_gpu(dut):
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
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await RisingEdge(dut.clk)
    dut.reset.value = 0
    await Timer(1, unit="ns")


async def write_inst(dut, addr, inst):
    await FallingEdge(dut.clk)
    dut.host_inst_we.value = 1
    dut.host_inst_addr.value = addr
    dut.host_inst_data.value = inst
    await RisingEdge(dut.clk)
    dut.host_inst_we.value = 0


async def write_mem(dut, addr, data):
    await FallingEdge(dut.clk)
    dut.host_mem_we.value = 1
    dut.host_mem_re.value = 0
    dut.host_mem_addr.value = addr
    dut.host_mem_wdata.value = data
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


async def launch(dut, block_count):
    await FallingEdge(dut.clk)
    dut.launch.value = 1
    dut.block_count.value = block_count
    await RisingEdge(dut.clk)
    dut.launch.value = 0
    await Timer(1, unit="ns")


async def wait_until_done(dut):
    for _ in range(200):
        await RisingEdge(dut.clk)
        if int(dut.done.value) == 1 and int(dut.busy.value) == 0:
            return
    raise AssertionError("GPU did not finish")


@cocotb.test()
async def test_gpu_one_core_program(dut):
    """One block loads a byte, doubles it, and stores the result"""

    await start_gpu(dut)

    # mem[0] = 15. R1 = 15, R2 = 30, mem[15] = 30.
    await write_mem(dut, 0, 15)
    program = [
        encode_inst(OP_LDR, rdst=1, rsrc1=0),
        encode_inst(OP_ADD, rdst=2, rsrc1=1, rsrc2=1),
        encode_inst(OP_STR, rsrc1=1, rsrc2=2),
        encode_inst(OP_HALT),
    ]
    for addr, inst in enumerate(program):
        await write_inst(dut, addr, inst)

    await launch(dut, block_count=1)
    await wait_until_done(dut)

    assert await read_mem(dut, 0) == 15, "Source byte was overwritten"
    assert await read_mem(dut, 15) == 30, "Stored result was not 15 + 15"


@cocotb.test()
async def test_gpu_four_blocks_and_empty_launch(dut):
    """Four HALT blocks all return to idle, and a zero-length launch completes"""

    await start_gpu(dut)
    await write_inst(dut, 0, encode_inst(OP_HALT))

    await launch(dut, block_count=4)
    await wait_until_done(dut)
    assert dut.busy.value == 0, "busy stayed high after four blocks"
    assert dut.done.value == 1, "done did not rise after four blocks"

    # A new launch with no blocks completes without starting work.
    await launch(dut, block_count=0)
    assert dut.busy.value == 0, "Empty launch raised busy"
    assert dut.done.value == 1, "Empty launch did not complete"
