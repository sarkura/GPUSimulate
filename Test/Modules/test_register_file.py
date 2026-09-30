# ============================================================================
# File: Test/Modules/test_register_file.py
# Description: Cocotb test cases for 8-bit Tiny-GPU register file.
# ============================================================================

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

# Architecture parameters, matching Source/Includes/defines.vh
REG_NUM = 8
DATA_MASK = 0xFF

# ============================================================
# Clock / RisingEdge
# ============================================================
#
# One clock period runs from one rising edge to the next:
#
#       RisingEdge                  RisingEdge
#           ↓                           ↓
#           ↑                           ↑
#           │                           │
#      ┌────┘                           └────┐
#      │                                     │
#      │                                     │
# ─────┘                                     └─────
#      ↑                                     ↑
#     0 → 1                                 0 → 1
#
#      └────────── one clock period ──────────┘
#
#
# Cocotb:
#
#     await RisingEdge(dut.clk)
#
#     ↓
#
#     Wait until clk goes from 0 to 1.
#
#     This does not generate a clock period. It waits
#     for the hardware clock to produce one rising edge.
#
#
# Synchronous write in the register file:
#
#     write_en = 1
#     write_addr = 3
#     write_data = 0x5A
#
#             │
#             │  wait
#             ↓
#
#        RisingEdge(clk)
#             │
#             ↓
#       R3 ← 0x5A
#
# Therefore:
#
#     Write inputs are set up
#             ↓
#       Wait for RisingEdge
#             ↓
#        The write is committed
#
# ============================================================

# Verilog:
#
#     always @(posedge clk)
#
#                  ↕
#
# Cocotb:
#
#     await RisingEdge(dut.clk)
#
# Both refer to the same hardware event:
#
#                 clk
#                  │
#                  ↓
#              0 → 1
#                  │
#              Rising Edge

def init_inputs(dut):
    """Drive every input to a known idle state before the clock starts"""
    dut.reset.value = 0
    dut.write_en.value = 0
    dut.write_addr.value = 0
    dut.write_data.value = 0
    dut.read_addr_a.value = 0
    dut.read_addr_b.value = 0


async def start_clocked_dut(dut):
    """Start a 10 ns clock and apply asynchronous reset"""
    init_inputs(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await Timer(1, unit="ns")

    dut.reset.value = 1
    await RisingEdge(dut.clk)
    dut.reset.value = 0
    await Timer(1, unit="ns")


async def write_register(dut, addr, data):
    """Commit write_data into registers[addr] on the next rising edge"""
    await FallingEdge(dut.clk)
    dut.write_addr.value = addr
    dut.write_data.value = data & DATA_MASK
    dut.write_en.value = 1
    await RisingEdge(dut.clk)
    dut.write_en.value = 0


@cocotb.test()
async def test_register_file_basic_operations(dut):
    """Verify reset, synchronous write, combinational dual-port read, and write enable"""

    await start_clocked_dut(dut)

    # 1. Reset clears every register on both read ports
    for addr in range(REG_NUM):
        dut.read_addr_a.value = addr
        dut.read_addr_b.value = addr
        await Timer(1, unit="ns")
        assert dut.read_data_a.value == 0, f"Reset failed on port A, R{addr} = {dut.read_data_a.value}"
        assert dut.read_data_b.value == 0, f"Reset failed on port B, R{addr} = {dut.read_data_b.value}"

    # 2. Write a unique value to each register and read it back
    for addr in range(REG_NUM):
        await write_register(dut, addr, 0x10 + addr)

    for addr in range(REG_NUM):
        dut.read_addr_a.value = addr
        await Timer(1, unit="ns")
        assert dut.read_data_a.value == 0x10 + addr, (
            f"Port A R{addr} read failed: {dut.read_data_a.value} != {0x10 + addr}"
        )

        dut.read_addr_b.value = addr
        await Timer(1, unit="ns")
        assert dut.read_data_b.value == 0x10 + addr, (
            f"Port B R{addr} read failed: {dut.read_data_b.value} != {0x10 + addr}"
        )

    # 3. Both ports can read different registers in the same cycle
    dut.read_addr_a.value = 1
    dut.read_addr_b.value = 6
    await Timer(1, unit="ns")
    assert dut.read_data_a.value == 0x11, f"Dual-port A failed: {dut.read_data_a.value} != 0x11"
    assert dut.read_data_b.value == 0x16, f"Dual-port B failed: {dut.read_data_b.value} != 0x16"

    # Both ports can also read the same register
    dut.read_addr_a.value = 4
    dut.read_addr_b.value = 4
    await Timer(1, unit="ns")
    assert dut.read_data_a.value == 0x14, f"Same-address port A failed: {dut.read_data_a.value} != 0x14"
    assert dut.read_data_b.value == 0x14, f"Same-address port B failed: {dut.read_data_b.value} != 0x14"

    # 4. write_en = 0 must not change the selected register
    await FallingEdge(dut.clk)
    dut.write_addr.value = 3
    dut.write_data.value = 0xAA
    dut.write_en.value = 0
    await RisingEdge(dut.clk)

    dut.read_addr_a.value = 3
    await Timer(1, unit="ns")
    assert dut.read_data_a.value == 0x13, f"Write leaked with write_en low: {dut.read_data_a.value} != 0x13"

    # 5. A write is committed only on the rising edge, then an overwrite replaces it
    await FallingEdge(dut.clk)
    dut.read_addr_a.value = 3
    dut.write_addr.value = 3
    dut.write_data.value = 0x5A
    dut.write_en.value = 1
    await Timer(1, unit="ns")
    assert dut.read_data_a.value == 0x13, "Write became visible before the rising edge"

    await RisingEdge(dut.clk)
    dut.write_en.value = 0
    await Timer(1, unit="ns")
    assert dut.read_data_a.value == 0x5A, f"Write not committed on rising edge: {dut.read_data_a.value} != 0x5A"

    # Neighbouring registers are left unchanged
    dut.read_addr_b.value = 2
    await Timer(1, unit="ns")
    assert dut.read_data_b.value == 0x12, f"R2 corrupted by R3 write: {dut.read_data_b.value} != 0x12"
    dut.read_addr_b.value = 4
    await Timer(1, unit="ns")
    assert dut.read_data_b.value == 0x14, f"R4 corrupted by R3 write: {dut.read_data_b.value} != 0x14"


@cocotb.test()
async def test_register_file_reset(dut):
    """Verify reset clears stored values and blocks a write while it is asserted"""

    await start_clocked_dut(dut)

    # 1. Fill the file, then reset must clear every register again
    for addr in range(REG_NUM):
        await write_register(dut, addr, 0x80 + addr)

    dut.reset.value = 1
    await Timer(1, unit="ns")  # Asynchronous reset, no clock edge required

    for addr in range(REG_NUM):
        dut.read_addr_a.value = addr
        dut.read_addr_b.value = addr
        await Timer(1, unit="ns")
        assert dut.read_data_a.value == 0, f"Async reset failed on port A, R{addr} = {dut.read_data_a.value}"
        assert dut.read_data_b.value == 0, f"Async reset failed on port B, R{addr} = {dut.read_data_b.value}"

    # 2. A write presented while reset is held must be discarded
    await FallingEdge(dut.clk)
    dut.write_addr.value = 2
    dut.write_data.value = 0xFF
    dut.write_en.value = 1
    await RisingEdge(dut.clk)

    dut.read_addr_a.value = 2
    await Timer(1, unit="ns")
    assert dut.read_data_a.value == 0, f"Write succeeded during reset: {dut.read_data_a.value} != 0"

    # 3. After reset is released, the discarded write must still be absent
    dut.reset.value = 0
    dut.write_en.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert dut.read_data_a.value == 0, f"Discarded write appeared after reset: {dut.read_data_a.value} != 0"
