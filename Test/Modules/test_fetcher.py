# ============================================================================
# File: Test/Modules/test_fetcher.py
# Description: Cocotb test cases for the Tiny-GPU instruction fetcher.
# ============================================================================

import cocotb
from cocotb.triggers import Timer


@cocotb.test()
async def test_fetcher_basic_operations(dut):
    """Verify the fetch address and the same-cycle instruction response"""

    # 1. An enabled fetch presents the PC and returns the instruction word
    dut.pc.value = 0x12
    dut.fetch_en.value = 1
    dut.inst.value = 0xABCD
    await Timer(1, unit="ns")

    assert dut.inst_addr.value == 0x12, f"inst_addr {int(dut.inst_addr.value)} != 0x12"
    assert dut.inst_out.value == 0xABCD, f"inst_out {int(dut.inst_out.value):04X} != ABCD"

    # 2. Changing the PC updates the address without a clock
    dut.pc.value = 0x07
    await Timer(1, unit="ns")
    assert dut.inst_addr.value == 0x07, f"inst_addr did not follow pc: {int(dut.inst_addr.value)}"

    # 3. fetch_en low forces a NOP while the address still follows the PC
    dut.fetch_en.value = 0
    dut.inst.value = 0xFFFF
    await Timer(1, unit="ns")
    assert dut.inst_out.value == 0, f"Disabled fetch returned {int(dut.inst_out.value):04X}"
    assert dut.inst_addr.value == 0x07, "Disabled fetch changed the address"
