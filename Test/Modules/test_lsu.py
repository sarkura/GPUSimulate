# ============================================================================
# File: Test/Modules/test_lsu.py
# Description: Cocotb test cases for one Tiny-GPU lane LSU.
# ============================================================================

import cocotb
from cocotb.triggers import Timer

MEM_CMD_IDLE  = 0x0
MEM_CMD_READ  = 0x1
MEM_CMD_WRITE = 0x2


async def drive(dut, exec_en, mem_cmd, addr, wdata):
    dut.exec_en.value = exec_en
    dut.mem_cmd.value = mem_cmd
    dut.addr.value = addr
    dut.wdata.value = wdata
    await Timer(1, unit="ns")


@cocotb.test()
async def test_lsu_basic_operations(dut):
    """Verify load and store requests, and that idle or disabled lanes do not request"""

    # 1. A load requests the read at Rsrc1. Store data is still presented.
    await drive(dut, exec_en=1, mem_cmd=MEM_CMD_READ, addr=0x10, wdata=0x22)
    assert dut.req_valid.value == 1, "Load did not request"
    assert dut.req_cmd.value == MEM_CMD_READ, f"Load cmd {int(dut.req_cmd.value)} != READ"
    assert dut.req_addr.value == 0x10, f"Load addr {int(dut.req_addr.value)} != 0x10"
    assert dut.req_wdata.value == 0x22, f"Load wdata {int(dut.req_wdata.value)} != 0x22"

    # 2. A store requests the write of Rsrc2 to MEM[Rsrc1]
    await drive(dut, exec_en=1, mem_cmd=MEM_CMD_WRITE, addr=0x3C, wdata=0xAB)
    assert dut.req_valid.value == 1, "Store did not request"
    assert dut.req_cmd.value == MEM_CMD_WRITE, f"Store cmd {int(dut.req_cmd.value)} != WRITE"
    assert dut.req_addr.value == 0x3C, f"Store addr {int(dut.req_addr.value)} != 0x3C"
    assert dut.req_wdata.value == 0xAB, f"Store wdata {int(dut.req_wdata.value):02X} != AB"

    # 3. IDLE keeps the address and data visible, but it is not a request
    await drive(dut, exec_en=1, mem_cmd=MEM_CMD_IDLE, addr=0x01, wdata=0x02)
    assert dut.req_valid.value == 0, "IDLE raised a request"
    assert dut.req_cmd.value == MEM_CMD_IDLE, "IDLE changed the command"
    assert dut.req_addr.value == 0x01, "IDLE dropped the address"
    assert dut.req_wdata.value == 0x02, "IDLE dropped the write data"

    # 4. exec_en low suppresses the request even for a read
    await drive(dut, exec_en=0, mem_cmd=MEM_CMD_READ, addr=0x44, wdata=0x55)
    assert dut.req_valid.value == 0, "Disabled lane raised a request"
    assert dut.req_addr.value == 0x44, "Disabled lane dropped the address"
    assert dut.req_wdata.value == 0x55, "Disabled lane dropped the write data"
