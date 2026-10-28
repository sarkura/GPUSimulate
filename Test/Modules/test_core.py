# ============================================================================
# File: Test/Modules/test_core.py
# Description: Cocotb test cases for the four-lane Tiny-GPU core.
# ============================================================================

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

# Instruction opcodes, matching Source/Includes/defines.vh
OP_NOP  = 0x0
OP_ADD  = 0x1
OP_SUB  = 0x2
OP_MUL  = 0x3
OP_AND  = 0x4
OP_OR   = 0x5
OP_LDR  = 0x8
OP_STR  = 0x9
OP_BR   = 0xC
OP_HALT = 0xF

MEM_CMD_IDLE  = 0x0
MEM_CMD_READ  = 0x1
MEM_CMD_WRITE = 0x2

DATA_MEM_WORDS = 256
LANE_NUM = 4


def encode_inst(opcode, rdst=0, rsrc1=0, rsrc2=0, reserved=0):
    """Pack one 16-bit instruction: opcode | rdst | rsrc1 | rsrc2 | reserved"""
    return (
        ((opcode & 0xF) << 12)
        | ((rdst & 0x7) << 9)
        | ((rsrc1 & 0x7) << 6)
        | ((rsrc2 & 0x7) << 3)
        | (reserved & 0x7)
    )


async def start_core(dut):
    """Reset, then pulse start. pc is 0 and the core is running."""
    dut.reset.value = 1
    dut.start.value = 0
    dut.stall.value = 0
    dut.inst.value = 0
    dut.mem_rdata.value = 0
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await RisingEdge(dut.clk)
    dut.reset.value = 0
    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0
    await Timer(1, unit="ns")
    assert dut.pc.value == 0, f"PC reset failed: {dut.pc.value}"
    assert dut.halted.value == 0, "Core halted out of reset"
    assert dut.idle.value == 0, "Core did not leave idle after start"


async def run_program(dut, imem, dmem):
    """Execute until HALT. Instruction and data memory are plain Python lists."""
    # A split memory instruction can take one cycle per lane.
    for _ in range(len(imem) * LANE_NUM + 8):
        await FallingEdge(dut.clk)
        pc = int(dut.pc.value)
        dut.inst.value = imem[pc] if pc < len(imem) else encode_inst(OP_HALT)
        await Timer(1, unit="ns")  # Wait for decode and register read

        cmd = int(dut.mem_cmd.value)
        addr = int(dut.mem_addr.value)
        wdata = int(dut.mem_wdata.value)
        dut.mem_rdata.value = dmem[addr]
        if cmd == MEM_CMD_WRITE:
            dmem[addr] = wdata

        await RisingEdge(dut.clk)
        if int(dut.halted.value) == 1:
            return pc

    raise AssertionError("Program did not halt")


@cocotb.test()
async def test_core_alu_and_memory(dut):
    """Run LDR/ALU/STR/NOP/HALT and check results written to data memory"""

    # mem[0] = 1, mem[1] = 15, mem[2] = 27. R0 stays 0 and is the first address.
    dmem = [0] * DATA_MEM_WORDS
    dmem[0] = 1
    dmem[1] = 15
    dmem[2] = 27

    imem = [
        encode_inst(OP_LDR, rdst=1, rsrc1=0),           # R1 = mem[0] = 1
        encode_inst(OP_LDR, rdst=2, rsrc1=1),           # R2 = mem[1] = 15
        encode_inst(OP_ADD, rdst=1, rsrc1=1, rsrc2=1),  # R1 = 2
        encode_inst(OP_LDR, rdst=3, rsrc1=1),           # R3 = mem[2] = 27
        encode_inst(OP_ADD, rdst=4, rsrc1=2, rsrc2=3),  # R4 = 42
        encode_inst(OP_STR, rsrc1=1, rsrc2=4),          # mem[2] = 42
        encode_inst(OP_SUB, rdst=5, rsrc1=3, rsrc2=2),  # R5 = 12
        encode_inst(OP_MUL, rdst=6, rsrc1=2, rsrc2=1),  # R6 = 30
        encode_inst(OP_ADD, rdst=1, rsrc1=1, rsrc2=1),  # R1 = 4
        encode_inst(OP_STR, rsrc1=1, rsrc2=6),          # mem[4] = 30
        encode_inst(OP_ADD, rdst=1, rsrc1=1, rsrc2=1),  # R1 = 8
        encode_inst(OP_STR, rsrc1=1, rsrc2=5),          # mem[8] = 12
        encode_inst(OP_AND, rdst=6, rsrc1=2, rsrc2=3),  # R6 = 15 & 27 = 11
        encode_inst(OP_OR,  rdst=7, rsrc1=2, rsrc2=3),  # R7 = 15 | 27 = 31
        encode_inst(OP_ADD, rdst=1, rsrc1=1, rsrc2=1),  # R1 = 16
        encode_inst(OP_STR, rsrc1=1, rsrc2=6),          # mem[16] = 11
        encode_inst(OP_ADD, rdst=1, rsrc1=1, rsrc2=1),  # R1 = 32
        encode_inst(OP_STR, rsrc1=1, rsrc2=7),          # mem[32] = 31
        encode_inst(OP_NOP),
        encode_inst(OP_HALT),
    ]

    await start_core(dut)
    halt_pc = await run_program(dut, imem, dmem)

    assert halt_pc == len(imem) - 1, f"HALT PC {halt_pc} != {len(imem) - 1}"
    assert dmem[2] == 42, f"ADD store failed: mem[2] = {dmem[2]}"
    assert dmem[4] == 30, f"MUL store failed: mem[4] = {dmem[4]}"
    assert dmem[8] == 12, f"SUB store failed: mem[8] = {dmem[8]}"
    assert dmem[16] == 11, f"AND store failed: mem[16] = {dmem[16]}"
    assert dmem[32] == 31, f"OR store failed: mem[32] = {dmem[32]}"

    # HALT holds the PC across another clock
    await RisingEdge(dut.clk)
    assert dut.pc.value == halt_pc, f"PC moved after HALT: {dut.pc.value}"
    assert dut.halted.value == 1, "halted cleared after HALT"


@cocotb.test()
async def test_core_branch_and_halt(dut):
    """BR jumps to Rsrc1 and skips the store in the fall-through slot"""

    # mem[0] is both the load address source (R0 == 0) and the branch target value.
    dmem = [0] * DATA_MEM_WORDS
    dmem[0] = 3

    imem = [
        encode_inst(OP_LDR, rdst=1, rsrc1=0),  # R1 = 3
        encode_inst(OP_BR, rsrc1=1),           # PC <- 3
        encode_inst(OP_STR, rsrc1=0, rsrc2=2), # skipped; R2 is 0, so this would clear mem[0]
        encode_inst(OP_HALT),
    ]

    await start_core(dut)
    halt_pc = await run_program(dut, imem, dmem)

    assert halt_pc == 3, f"Branch landed at PC {halt_pc} != 3"
    assert dmem[0] == 3, f"Skipped STR wrote memory: mem[0] = {dmem[0]}"
    assert dut.halted.value == 1, "Core did not stay halted"
    assert dut.mem_cmd.value == MEM_CMD_IDLE, "Memory command not idle after HALT"


def lane_pc(dut, lane):
    """Lane PCs are packed with lane 0 in the low byte"""
    return (int(dut.lane_pc.value) >> (8 * lane)) & 0xFF


@cocotb.test()
async def test_core_lane_stores(dut):
    """Lanes that share a PC store different addresses through R7, the lane index"""

    dmem = [0] * DATA_MEM_WORDS
    dmem[0] = 16
    imem = [
        encode_inst(OP_LDR, rdst=1, rsrc1=0),          # R1 = 16, one coalesced read
        encode_inst(OP_ADD, rdst=2, rsrc1=1, rsrc2=7),  # R2 = 16 + lane
        encode_inst(OP_STR, rsrc1=2, rsrc2=2),          # mem[16 + lane] = 16 + lane
        encode_inst(OP_HALT),
    ]

    await start_core(dut)
    halt_pc = await run_program(dut, imem, dmem)

    assert halt_pc == 3, f"Store program halted at PC {halt_pc}"
    assert [dmem[16 + lane] for lane in range(LANE_NUM)] == [16, 17, 18, 19], (
        f"Per-lane stores failed: {[dmem[16 + lane] for lane in range(LANE_NUM)]}"
    )


@cocotb.test()
async def test_core_lane_branch(dut):
    """A diverged branch sends each lane to its own HALT"""

    # Targets are 3, 4, 5, and 6, and each of those words is HALT.
    dmem = [0] * DATA_MEM_WORDS
    dmem[0] = 3
    imem = [
        encode_inst(OP_LDR, rdst=1, rsrc1=0),          # R1 = 3
        encode_inst(OP_ADD, rdst=1, rsrc1=1, rsrc2=7),  # R1 = 3 + lane
        encode_inst(OP_BR, rsrc1=1),
        encode_inst(OP_HALT),
        encode_inst(OP_HALT),
        encode_inst(OP_HALT),
        encode_inst(OP_HALT),
    ]

    await start_core(dut)
    await run_program(dut, imem, dmem)

    assert [lane_pc(dut, lane) for lane in range(LANE_NUM)] == [3, 4, 5, 6], (
        f"Diverged HALT PCs were {[lane_pc(dut, lane) for lane in range(LANE_NUM)]}"
    )
    assert dut.halted.value == 1, "Core did not halt after every lane reached HALT"
