# ============================================================================
# File: Test/Modules/test_alu.py
# Description: Cocotb test cases for 8-bit Tiny-GPU ALU.
# ============================================================================

import cocotb
from cocotb.triggers import Timer

# ALU opcodes (4-bit), matching those defined in Source/Includes/defines.vh
ALU_NOP = 0x0
ALU_ADD = 0x1
ALU_SUB = 0x2
ALU_MUL = 0x3
ALU_AND = 0x4
ALU_OR  = 0x5
ALU_XOR = 0x6
ALU_NOT = 0x7
ALU_SHL = 0x8
ALU_SHR = 0x9


def to_signed_8bit(val):
    """Convert an unsigned integer to an 8-bit two's complement signed integer"""
    val = val & 0xFF
    return val if val < 128 else val - 256


@cocotb.test()
async def test_alu_basic_operations(dut):
    """Verify basic arithmetic and logic operations (ADD, SUB, MUL, AND, OR, XOR, NOT, SHL, SHR)"""

    # 1. Addition and Zero Flag test
    dut.a.value = 15
    dut.b.value = 20
    dut.alu_op.value = ALU_ADD
    await Timer(1, unit="ns")  # Wait for combinational logic to settle

    assert dut.result.value == 35, f"ADD Failed: {dut.result.value} != 35"
    assert dut.zero.value == 0, "Zero flag incorrectly set"

    # 2. Subtraction resulting in zero (20 - 20 = 0)
    dut.a.value = 20
    dut.b.value = 20
    dut.alu_op.value = ALU_SUB
    await Timer(1, unit="ns")

    assert dut.result.value == 0, f"SUB Failed: {dut.result.value} != 0"
    assert dut.zero.value == 1, "Zero flag not set on zero result"

    # 3. Multiplication with truncation to low 8 bits (15 * 20 = 300 -> 300 % 256 = 44)
    dut.a.value = 15
    dut.b.value = 20
    dut.alu_op.value = ALU_MUL
    await Timer(1, unit="ns")

    assert dut.result.value == 44, f"MUL Truncation Failed: {dut.result.value} != 44"

    # 4. Bitwise logic operations (AND, OR, XOR, NOT)
    dut.a.value = 0b1100_1010
    dut.b.value = 0b1010_0101

    dut.alu_op.value = ALU_AND
    await Timer(1, unit="ns")
    assert dut.result.value == 0b1000_0000, "AND Failed"

    dut.alu_op.value = ALU_OR
    await Timer(1, unit="ns")
    assert dut.result.value == 0b1110_1111, "OR Failed"

    dut.alu_op.value = ALU_XOR
    await Timer(1, unit="ns")
    assert dut.result.value == 0b0110_1111, "XOR Failed"

    dut.alu_op.value = ALU_NOT
    await Timer(1, unit="ns")
    assert dut.result.value == 0b0011_0101, "NOT Failed"

    # 5. Shift operations (A << B[2:0], A >> B[2:0])
    dut.a.value = 0b0000_0011  # 3
    dut.b.value = 2            # Shift by 2 bits
    dut.alu_op.value = ALU_SHL
    await Timer(1, unit="ns")
    assert dut.result.value == 0b0000_1100, "SHL Failed"

    dut.alu_op.value = ALU_SHR
    await Timer(1, unit="ns")
    assert dut.result.value == 0b0000_0000, "SHR Failed"


@cocotb.test()
async def test_alu_overflow_flag(dut):
    """Verify the Overflow Flag for signed addition and subtraction"""

    # 1. Positive + positive yields negative (positive overflow): 120 + 10 = 130 (-126)
    dut.a.value = 120
    dut.b.value = 10
    dut.alu_op.value = ALU_ADD
    await Timer(1, unit="ns")

    assert dut.overflow.value == 1, "Overflow flag failed on positive overflow"

    # 2. Positive + negative (no overflow): 120 + (-10) = 110
    dut.a.value = 120
    dut.b.value = (-10) & 0xFF  # Convert to 8-bit unsigned two's complement
    dut.alu_op.value = ALU_ADD
    await Timer(1, unit="ns")

    assert dut.overflow.value == 0, "Overflow flag falsely triggered on opposite sign ADD"

    # 3. Negative - positive (negative overflow): -100 - 40 = -140 (below -128)
    dut.a.value = (-100) & 0xFF
    dut.b.value = 40
    dut.alu_op.value = ALU_SUB
    await Timer(1, unit="ns")

    assert dut.overflow.value == 1, "Overflow flag failed on negative overflow in SUB"
