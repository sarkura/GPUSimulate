# ============================================================================
# File: Test/Modules/test_decoder.py
# Description: Cocotb test cases for the Tiny-GPU instruction decoder.
# ============================================================================

import cocotb
from cocotb.triggers import Timer

# Instruction opcodes (4-bit), matching Source/Includes/defines.vh
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

# ALU opcodes produced by the decoder
ALU_NOP = 0x0
ALU_ADD = 0x1
ALU_SUB = 0x2
ALU_MUL = 0x3
ALU_AND = 0x4
ALU_OR  = 0x5

# Memory controller commands
MEM_CMD_IDLE  = 0x0
MEM_CMD_READ  = 0x1
MEM_CMD_WRITE = 0x2


def encode_inst(opcode, rdst=0, rsrc1=0, rsrc2=0, reserved=0):
    """Pack one 16-bit instruction: opcode | rdst | rsrc1 | rsrc2 | reserved"""
    return (
        ((opcode & 0xF) << 12)
        | ((rdst & 0x7) << 9)
        | ((rsrc1 & 0x7) << 6)
        | ((rsrc2 & 0x7) << 3)
        | (reserved & 0x7)
    )


async def check_decode(dut, inst, opcode, rdst, rsrc1, rsrc2,
                       alu_op, reg_write_en, mem_cmd, branch, halt):
    """Drive one instruction and wait for combinational decode to settle"""
    dut.inst.value = inst
    await Timer(1, unit="ns")

    assert dut.opcode.value == opcode, f"opcode {int(dut.opcode.value):X} != {opcode:X}"
    assert dut.rdst.value == rdst, f"rdst {int(dut.rdst.value)} != {rdst}"
    assert dut.rsrc1.value == rsrc1, f"rsrc1 {int(dut.rsrc1.value)} != {rsrc1}"
    assert dut.rsrc2.value == rsrc2, f"rsrc2 {int(dut.rsrc2.value)} != {rsrc2}"
    assert dut.alu_op.value == alu_op, f"alu_op {int(dut.alu_op.value):X} != {alu_op:X}"
    assert dut.reg_write_en.value == reg_write_en, (
        f"reg_write_en {int(dut.reg_write_en.value)} != {reg_write_en}"
    )
    assert dut.mem_cmd.value == mem_cmd, f"mem_cmd {int(dut.mem_cmd.value)} != {mem_cmd}"
    assert dut.branch.value == branch, f"branch {int(dut.branch.value)} != {branch}"
    assert dut.halt.value == halt, f"halt {int(dut.halt.value)} != {halt}"


@cocotb.test()
async def test_decoder_basic_operations(dut):
    """Verify field extract and ALU opcode mapping (NOP, ADD, SUB, MUL, AND, OR)"""

    # 1. Field extract: ADD R7, R3, R5 with reserved bits set
    await check_decode(
        dut,
        encode_inst(OP_ADD, rdst=7, rsrc1=3, rsrc2=5, reserved=0b111),
        opcode=OP_ADD, rdst=7, rsrc1=3, rsrc2=5,
        alu_op=ALU_ADD, reg_write_en=1, mem_cmd=MEM_CMD_IDLE, branch=0, halt=0,
    )

    # 2. NOP leaves every control signal idle
    await check_decode(
        dut,
        encode_inst(OP_NOP, rdst=1, rsrc1=2, rsrc2=3),
        opcode=OP_NOP, rdst=1, rsrc1=2, rsrc2=3,
        alu_op=ALU_NOP, reg_write_en=0, mem_cmd=MEM_CMD_IDLE, branch=0, halt=0,
    )

    # 3. Register ALU ops write the destination and do not touch memory or control flow
    alu_ops = [
        (OP_SUB, ALU_SUB),
        (OP_MUL, ALU_MUL),
        (OP_AND, ALU_AND),
        (OP_OR,  ALU_OR),
    ]
    for opcode, alu_op in alu_ops:
        await check_decode(
            dut,
            encode_inst(opcode, rdst=4, rsrc1=1, rsrc2=2),
            opcode=opcode, rdst=4, rsrc1=1, rsrc2=2,
            alu_op=alu_op, reg_write_en=1, mem_cmd=MEM_CMD_IDLE, branch=0, halt=0,
        )


@cocotb.test()
async def test_decoder_memory_and_control(dut):
    """Verify LDR, STR, BR, HALT, and illegal opcodes"""

    # 1. LDR R2, [R6]: write the loaded data back, issue a memory read
    await check_decode(
        dut,
        encode_inst(OP_LDR, rdst=2, rsrc1=6, rsrc2=0),
        opcode=OP_LDR, rdst=2, rsrc1=6, rsrc2=0,
        alu_op=ALU_NOP, reg_write_en=1, mem_cmd=MEM_CMD_READ, branch=0, halt=0,
    )

    # 2. STR [R1], R4: memory write, no register write
    await check_decode(
        dut,
        encode_inst(OP_STR, rdst=0, rsrc1=1, rsrc2=4),
        opcode=OP_STR, rdst=0, rsrc1=1, rsrc2=4,
        alu_op=ALU_NOP, reg_write_en=0, mem_cmd=MEM_CMD_WRITE, branch=0, halt=0,
    )

    # 3. BR raises branch and does not write
    await check_decode(
        dut,
        encode_inst(OP_BR, rdst=0, rsrc1=7, rsrc2=0),
        opcode=OP_BR, rdst=0, rsrc1=7, rsrc2=0,
        alu_op=ALU_NOP, reg_write_en=0, mem_cmd=MEM_CMD_IDLE, branch=1, halt=0,
    )

    # 4. HALT raises halt and does not write
    await check_decode(
        dut,
        encode_inst(OP_HALT),
        opcode=OP_HALT, rdst=0, rsrc1=0, rsrc2=0,
        alu_op=ALU_NOP, reg_write_en=0, mem_cmd=MEM_CMD_IDLE, branch=0, halt=1,
    )

    # 5. An undefined opcode behaves as NOP. 0x6 is not an instruction opcode.
    await check_decode(
        dut,
        encode_inst(0x6, rdst=3, rsrc1=1, rsrc2=2),
        opcode=0x6, rdst=3, rsrc1=1, rsrc2=2,
        alu_op=ALU_NOP, reg_write_en=0, mem_cmd=MEM_CMD_IDLE, branch=0, halt=0,
    )
