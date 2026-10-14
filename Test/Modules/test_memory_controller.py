# ============================================================================
# File: Test/Modules/test_memory_controller.py
# Description: Cocotb test cases for the Tiny-GPU data memory controller.
# ============================================================================

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

# Memory commands, matching Source/Includes/defines.vh
MEM_CMD_IDLE  = 0x0
MEM_CMD_READ  = 0x1
MEM_CMD_WRITE = 0x2
MEM_CMD_BAD   = 0x3

DATA_MASK = 0xFF


def init_inputs(dut):
    """Drive every input to a known idle state before the clock starts"""
    dut.reset.value = 0
    dut.mem_cmd.value = MEM_CMD_IDLE
    dut.mem_addr.value = 0
    dut.mem_wdata.value = 0


async def start_clocked_dut(dut):
    """Start a 10 ns clock and apply asynchronous reset"""
    init_inputs(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await Timer(1, unit="ns")

    dut.reset.value = 1
    await RisingEdge(dut.clk)
    dut.reset.value = 0
    await Timer(1, unit="ns")


async def write_mem(dut, addr, data):
    """Commit mem_wdata into mem[addr] on the next rising edge"""
    await FallingEdge(dut.clk)
    dut.mem_addr.value = addr
    dut.mem_wdata.value = data & DATA_MASK
    dut.mem_cmd.value = MEM_CMD_WRITE
    await RisingEdge(dut.clk)
    dut.mem_cmd.value = MEM_CMD_IDLE


async def expect_read(dut, addr, expected):
    """Combinational read: the result follows the address without a clock edge"""
    dut.mem_cmd.value = MEM_CMD_READ
    dut.mem_addr.value = addr
    await Timer(1, unit="ns")
    assert dut.mem_rdata.value == expected, (
        f"Read mem[{addr}] failed: {int(dut.mem_rdata.value)} != {expected}"
    )


@cocotb.test()
async def test_memory_controller_basic_operations(dut):
    """Verify reset, synchronous write, combinational read, and idle"""

    await start_clocked_dut(dut)

    # 1. Reset leaves every probed address reading as zero
    for addr in (0, 1, 127, 255):
        await expect_read(dut, addr, 0)

    # 2. Write distinct bytes and read them back
    samples = {0: 0x11, 1: 0x22, 127: 0x7F, 255: 0xA5}
    for addr, data in samples.items():
        await write_mem(dut, addr, data)
    for addr, data in samples.items():
        await expect_read(dut, addr, data)

    # 3. A write returns zeros while it is pending, then the new byte is readable
    await FallingEdge(dut.clk)
    dut.mem_addr.value = 1
    dut.mem_wdata.value = 0x5A
    dut.mem_cmd.value = MEM_CMD_WRITE
    await Timer(1, unit="ns")
    assert dut.mem_rdata.value == 0, "Write drove read data before the rising edge"

    await RisingEdge(dut.clk)
    dut.mem_cmd.value = MEM_CMD_READ
    await Timer(1, unit="ns")
    assert dut.mem_rdata.value == 0x5A, f"Write not committed: {int(dut.mem_rdata.value)} != 0x5A"

    # Neighbouring locations stay unchanged
    await expect_read(dut, 0, 0x11)
    await expect_read(dut, 127, 0x7F)

    # 4. IDLE returns zeros and does not store the presented write data
    await FallingEdge(dut.clk)
    dut.mem_cmd.value = MEM_CMD_IDLE
    dut.mem_addr.value = 0
    dut.mem_wdata.value = 0xFF
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert dut.mem_rdata.value == 0, f"IDLE returned data: {int(dut.mem_rdata.value)}"
    await expect_read(dut, 0, 0x11)


@cocotb.test()
async def test_memory_controller_reset(dut):
    """Verify reset clears stored bytes and discards a write while it is asserted"""

    await start_clocked_dut(dut)

    # 1. Fill several locations, then reset must clear them without a further write
    for addr, data in ((3, 0x80), (4, 0x81), (5, 0x82)):
        await write_mem(dut, addr, data)

    dut.reset.value = 1
    await Timer(1, unit="ns")  # Asynchronous reset, no clock edge required
    for addr in (3, 4, 5):
        await expect_read(dut, addr, 0)

    # 2. A write presented while reset is held must be discarded
    await FallingEdge(dut.clk)
    dut.mem_cmd.value = MEM_CMD_WRITE
    dut.mem_addr.value = 3
    dut.mem_wdata.value = 0xFF
    await RisingEdge(dut.clk)

    dut.reset.value = 0
    dut.mem_cmd.value = MEM_CMD_IDLE
    await RisingEdge(dut.clk)
    await expect_read(dut, 3, 0)

    # 3. An undefined command neither writes nor returns data
    await FallingEdge(dut.clk)
    dut.mem_cmd.value = MEM_CMD_BAD
    dut.mem_addr.value = 4
    dut.mem_wdata.value = 0xAB
    await Timer(1, unit="ns")
    assert dut.mem_rdata.value == 0, "Undefined command returned data"
    await RisingEdge(dut.clk)
    dut.mem_cmd.value = MEM_CMD_IDLE
    await expect_read(dut, 4, 0)
