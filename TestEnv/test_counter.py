import cocotb
from cocotb.triggers import Timer, RisingEdge
from cocotb.clock import Clock

@cocotb.test()
async def test_counter_basic(dut):
    """test the counter increment logic"""
    # enable clock (unit="ns")
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # reset signal test
    dut.rst.value = 1
    await Timer(20, unit="ns")
    dut.rst.value = 0
    await RisingEdge(dut.clk)

    # verify reset value is 0
    assert dut.count.value == 0, f"Reset failed, count is {dut.count.value}"

    # the counter run 5 clock cycles
    for i in range(1, 6):
        await RisingEdge(dut.clk)
        assert dut.count.value == i, f"Expected {i}, got {dut.count.value}"

    dut._log.info("Env Verification Passed!")