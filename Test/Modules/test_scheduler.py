# ============================================================================
# File: Test/Modules/test_scheduler.py
# Description: Cocotb test cases for the Tiny-GPU lane scheduler.
# ============================================================================

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

LANE_NUM = 4


def pack_pcs(pcs):
    """Pack lane PCs with lane 0 in the low byte"""
    packed = 0
    for lane, pc in enumerate(pcs):
        packed |= (pc & 0xFF) << (8 * lane)
    return packed


def init_inputs(dut):
    dut.reset.value = 0
    dut.lane_pc.value = 0
    dut.lane_halted.value = 0
    dut.is_mem.value = 0
    dut.ack_mask.value = 0


async def start_clocked_dut(dut):
    init_inputs(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await Timer(1, unit="ns")
    dut.reset.value = 1
    await RisingEdge(dut.clk)
    dut.reset.value = 0
    await Timer(1, unit="ns")


@cocotb.test()
async def test_scheduler_basic_operations(dut):
    """Verify lowest-PC selection, halted lanes, and same-cycle ALU retire"""

    await start_clocked_dut(dut)

    # 1. Every lane at PC 0 is issued together, and a non-memory op retires now
    assert dut.issue_valid.value == 1, "No lane was eligible after reset"
    assert dut.issue_pc.value == 0, f"issue_pc {int(dut.issue_pc.value)} != 0"
    assert dut.exec_mask.value == 0b1111, f"exec_mask {int(dut.exec_mask.value):04b} != 1111"
    assert dut.retire.value == 1, "ALU-style issue did not retire"
    assert dut.serviced.value == 0, "serviced was set with no memory ack"

    # 2. The lowest PC wins, including every lane that shares it
    dut.lane_pc.value = pack_pcs([5, 3, 9, 3])
    await Timer(1, unit="ns")
    assert dut.issue_pc.value == 3, f"issue_pc {int(dut.issue_pc.value)} != 3"
    assert dut.exec_mask.value == 0b1010, f"exec_mask {int(dut.exec_mask.value):04b} != 1010"

    # 3. A halted lane is skipped even when its PC is the lowest
    dut.lane_pc.value = pack_pcs([4, 1, 4, 7])
    dut.lane_halted.value = 0b0010
    await Timer(1, unit="ns")
    assert dut.issue_pc.value == 4, f"issue_pc {int(dut.issue_pc.value)} != 4"
    assert dut.exec_mask.value == 0b0101, f"exec_mask {int(dut.exec_mask.value):04b} != 0101"
    assert dut.issue_valid.value == 1, "Active lanes were treated as halted"

    # 4. No eligible lane means the scheduler is idle
    dut.lane_halted.value = 0b1111
    await Timer(1, unit="ns")
    assert dut.issue_valid.value == 0, "issue_valid stayed high with every lane halted"
    assert dut.exec_mask.value == 0, f"exec_mask {int(dut.exec_mask.value):04b} was not empty"
    assert dut.retire.value == 0, "Idle scheduler retired an instruction"


@cocotb.test()
async def test_scheduler_memory_retire(dut):
    """Verify a memory instruction retires only after every selected lane is acked"""

    await start_clocked_dut(dut)
    dut.lane_pc.value = pack_pcs([0, 0, 0, 0])
    dut.lane_halted.value = 0
    dut.is_mem.value = 1
    dut.ack_mask.value = 0
    await Timer(1, unit="ns")
    assert dut.retire.value == 0, "Memory issue retired before any ack"
    assert dut.exec_mask.value == 0b1111, "Memory issue dropped lanes"

    # 1. One lane ack is recorded on the clock and does not retire the group
    dut.ack_mask.value = 0b0001
    await Timer(1, unit="ns")
    assert dut.retire.value == 0, "A single lane ack retired the whole group"
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert dut.serviced.value == 0b0001, f"serviced {int(dut.serviced.value):04b} != 0001"

    # 2. The remaining lanes can be acked together
    dut.ack_mask.value = 0b1110
    await Timer(1, unit="ns")
    assert dut.retire.value == 1, "The last acks did not retire the memory instruction"
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert dut.serviced.value == 0, f"serviced stuck after retire: {int(dut.serviced.value):04b}"

    # 3. Reset drops an in-progress mask
    dut.ack_mask.value = 0b0011
    await Timer(1, unit="ns")
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert dut.serviced.value == 0b0011, "Partial ack was not recorded before reset"

    dut.reset.value = 1
    await Timer(1, unit="ns")
    assert dut.serviced.value == 0, "Reset left serviced set"
    dut.reset.value = 0
    dut.ack_mask.value = 0
    await Timer(1, unit="ns")
    assert dut.retire.value == 0, "Clearing reset retired a memory instruction with no ack"
