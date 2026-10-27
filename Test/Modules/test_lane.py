# ============================================================================
# File: Test/Modules/test_lane.py
# Description: Cocotb test cases for one Tiny-GPU SIMD lane.
# Elaborated with LANE_ID = 3, so R7 resets to 3.
# ============================================================================

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

ALU_NOP = 0x0
ALU_ADD = 0x1

MEM_CMD_IDLE  = 0x0
MEM_CMD_READ  = 0x1
MEM_CMD_WRITE = 0x2

LANE_ID = 3


def init_inputs(dut):
    dut.exec_en.value = 0
    dut.retire.value = 0
    dut.mem_ack.value = 0
    dut.alu_op.value = ALU_NOP
    dut.reg_write_en.value = 0
    dut.mem_cmd.value = MEM_CMD_IDLE
    dut.branch.value = 0
    dut.halt.value = 0
    dut.rdst.value = 0
    dut.rsrc1.value = 0
    dut.rsrc2.value = 0
    dut.mem_rdata.value = 0


async def start_clocked_dut(dut):
    init_inputs(dut)
    dut.reset.value = 1
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await RisingEdge(dut.clk)
    dut.reset.value = 0
    await Timer(1, unit="ns")


async def commit(dut):
    """Retire one non-memory operation on the next rising edge"""
    await FallingEdge(dut.clk)
    dut.exec_en.value = 1
    dut.retire.value = 1
    await RisingEdge(dut.clk)
    dut.retire.value = 0
    await Timer(1, unit="ns")


async def read_reg(dut, reg):
    """Observe a register through the LSU store-data output without retiring"""
    dut.exec_en.value = 1
    dut.retire.value = 0
    dut.mem_ack.value = 0
    dut.reg_write_en.value = 0
    dut.mem_cmd.value = MEM_CMD_WRITE
    dut.branch.value = 0
    dut.halt.value = 0
    dut.rsrc1.value = 0
    dut.rsrc2.value = reg
    await Timer(1, unit="ns")
    return int(dut.req_wdata.value)


@cocotb.test()
async def test_lane_basic_operations(dut):
    """Verify reset, R7 lane id, ALU write-back, and the PC retire gates"""

    await start_clocked_dut(dut)
    assert dut.pc.value == 0, f"PC reset failed: {int(dut.pc.value)}"
    assert dut.halted.value == 0, "Lane halted out of reset"
    assert dut.req_valid.value == 0, "Lane requested memory out of reset"

    # 1. R7 is the lane index. R0 stays 0, so the address of this probe is 0.
    dut.exec_en.value = 1
    dut.mem_cmd.value = MEM_CMD_WRITE
    dut.rsrc1.value = 0
    dut.rsrc2.value = 7
    await Timer(1, unit="ns")
    assert dut.req_valid.value == 1, "Store probe did not request"
    assert dut.req_addr.value == 0, f"R0 read {int(dut.req_addr.value)} != 0"
    assert dut.req_wdata.value == LANE_ID, f"R7 read {int(dut.req_wdata.value)} != {LANE_ID}"

    # 2. ADD R1, R7, R7 commits on retire and advances the PC
    await FallingEdge(dut.clk)
    dut.exec_en.value = 1
    dut.retire.value = 1
    dut.mem_ack.value = 0
    dut.alu_op.value = ALU_ADD
    dut.reg_write_en.value = 1
    dut.mem_cmd.value = MEM_CMD_IDLE
    dut.branch.value = 0
    dut.halt.value = 0
    dut.rdst.value = 1
    dut.rsrc1.value = 7
    dut.rsrc2.value = 7
    await RisingEdge(dut.clk)
    dut.retire.value = 0
    await Timer(1, unit="ns")
    assert dut.pc.value == 1, f"PC did not advance: {int(dut.pc.value)}"
    assert await read_reg(dut, 1) == LANE_ID * 2, "ADD R1, R7, R7 failed"

    # 3. retire low holds the PC, and exec_en low blocks both the write and the PC
    pc_before = int(dut.pc.value)
    await FallingEdge(dut.clk)
    dut.exec_en.value = 1
    dut.retire.value = 0
    dut.mem_cmd.value = MEM_CMD_IDLE
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert dut.pc.value == pc_before, "PC advanced without retire"

    await FallingEdge(dut.clk)
    dut.exec_en.value = 0
    dut.retire.value = 1
    dut.reg_write_en.value = 1
    dut.alu_op.value = ALU_ADD
    dut.rdst.value = 1
    dut.rsrc1.value = 7
    dut.rsrc2.value = 7
    await RisingEdge(dut.clk)
    dut.exec_en.value = 1
    dut.retire.value = 0
    dut.reg_write_en.value = 0
    await Timer(1, unit="ns")
    assert dut.pc.value == pc_before, "PC advanced while exec_en was low"
    assert await read_reg(dut, 1) == LANE_ID * 2, "Register write happened while exec_en was low"


@cocotb.test()
async def test_lane_branch_load_halt(dut):
    """Verify branch, a load that waits for mem_ack, and halt"""

    await start_clocked_dut(dut)

    # Seed R1 with 6 so the branch target is a register value.
    await FallingEdge(dut.clk)
    dut.alu_op.value = ALU_ADD
    dut.reg_write_en.value = 1
    dut.mem_cmd.value = MEM_CMD_IDLE
    dut.rdst.value = 1
    dut.rsrc1.value = 7
    dut.rsrc2.value = 7
    await commit(dut)
    assert await read_reg(dut, 1) == LANE_ID * 2, "Seed ADD failed"

    # 1. BR uses this lane's R1 and does not write a register
    await FallingEdge(dut.clk)
    dut.branch.value = 1
    dut.reg_write_en.value = 0
    dut.alu_op.value = ALU_NOP
    dut.rsrc1.value = 1
    await commit(dut)
    dut.branch.value = 0
    assert dut.pc.value == LANE_ID * 2, f"Branch PC {int(dut.pc.value)} != {LANE_ID * 2}"

    # 2. A load waits for mem_ack, then writes mem_rdata and retires
    await FallingEdge(dut.clk)
    dut.exec_en.value = 1
    dut.retire.value = 0
    dut.mem_ack.value = 0
    dut.mem_cmd.value = MEM_CMD_READ
    dut.reg_write_en.value = 1
    dut.rdst.value = 2
    dut.mem_rdata.value = 0x5A
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert dut.pc.value == LANE_ID * 2, "PC advanced before the load completed"
    assert await read_reg(dut, 2) == 0, "Load data was written before mem_ack"

    await FallingEdge(dut.clk)
    dut.exec_en.value = 1
    dut.retire.value = 1
    dut.mem_ack.value = 1
    dut.mem_cmd.value = MEM_CMD_READ
    dut.reg_write_en.value = 1
    dut.rdst.value = 2
    dut.mem_rdata.value = 0x5A
    await RisingEdge(dut.clk)
    dut.retire.value = 0
    dut.mem_ack.value = 0
    await Timer(1, unit="ns")
    assert dut.pc.value == LANE_ID * 2 + 1, f"PC {int(dut.pc.value)} did not retire the load"
    assert await read_reg(dut, 2) == 0x5A, f"Load wrote {await read_reg(dut, 2):02X} != 5A"

    # 3. HALT freezes the PC and suppresses later memory requests
    halt_pc = int(dut.pc.value)
    await FallingEdge(dut.clk)
    dut.exec_en.value = 1
    dut.retire.value = 1
    dut.halt.value = 1
    dut.branch.value = 0
    dut.reg_write_en.value = 0
    dut.mem_cmd.value = MEM_CMD_IDLE
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert dut.halted.value == 1, "halted did not rise"
    assert dut.pc.value == halt_pc, "HALT moved the PC"

    dut.mem_cmd.value = MEM_CMD_READ
    dut.exec_en.value = 1
    dut.retire.value = 1
    dut.branch.value = 1
    dut.rsrc1.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert dut.halted.value == 1, "halted cleared after HALT"
    assert dut.pc.value == halt_pc, "PC moved after HALT"
    assert dut.req_valid.value == 0, "Halted lane raised a memory request"
