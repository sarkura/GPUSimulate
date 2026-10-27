# ============================================================================
# File: Test/Modules/test_dispatcher.py
# Description: Cocotb test cases for the Tiny-GPU block dispatcher.
# ============================================================================

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer

CORE_NUM = 4


def init_inputs(dut):
    """Drive every input to a known idle state before the clock starts"""
    dut.reset.value = 0
    dut.launch.value = 0
    dut.block_count.value = 0
    dut.core_idle.value = 0


async def start_clocked_dut(dut):
    """Start a 10 ns clock and apply asynchronous reset"""
    init_inputs(dut)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await Timer(1, unit="ns")

    dut.reset.value = 1
    await RisingEdge(dut.clk)
    dut.reset.value = 0
    await Timer(1, unit="ns")


async def pulse_launch(dut, block_count):
    """One-cycle launch sampled on the next rising edge"""
    await FallingEdge(dut.clk)
    dut.launch.value = 1
    dut.block_count.value = block_count
    await RisingEdge(dut.clk)
    dut.launch.value = 0
    await Timer(1, unit="ns")


def expect_issue(dut, core, block_id):
    assert int(dut.busy.value) == 1, "Dispatcher went idle during issue"
    assert int(dut.done.value) == 0, "done rose before the job retired"
    assert int(dut.core_start.value) == (1 << core), (
        f"core_start {int(dut.core_start.value):04b} != core {core}"
    )
    assert int(dut.block_id.value) == block_id, (
        f"block_id {int(dut.block_id.value)} != {block_id}"
    )


def expect_idle_outputs(dut):
    assert int(dut.core_start.value) == 0, f"core_start stuck at {int(dut.core_start.value):04b}"
    assert int(dut.block_id.value) == 0, f"block_id stuck at {int(dut.block_id.value)}"


@cocotb.test()
async def test_dispatcher_basic_operations(dut):
    """Verify priority issue, one block per cycle, and retirement after the cores go idle"""

    await start_clocked_dut(dut)
    expect_idle_outputs(dut)
    assert int(dut.busy.value) == 0, "busy set out of reset"
    assert int(dut.done.value) == 0, "done set out of reset"

    # 1. Lowest-numbered idle core wins. Core 0 stays free, so it takes every block.
    dut.core_idle.value = 0b1111
    await pulse_launch(dut, 3)
    for block_id in range(3):
        expect_issue(dut, core=0, block_id=block_id)
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")

    # The launch is still in flight until the following edge sees every core idle.
    expect_idle_outputs(dut)
    assert int(dut.busy.value) == 1, "Job retired in the same cycle as the last issue"
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert int(dut.busy.value) == 0, "busy stayed high after every core went idle"
    assert int(dut.done.value) == 1, "done did not rise"
    expect_idle_outputs(dut)

    # 2. A busy core is skipped. Only core 2 can take the first block.
    dut.core_idle.value = 0b0100
    await pulse_launch(dut, 2)
    expect_issue(dut, core=2, block_id=0)

    # Core 2 accepts the block on this edge and then reports busy.
    await RisingEdge(dut.clk)
    dut.core_idle.value = 0b0000
    await Timer(1, unit="ns")
    expect_idle_outputs(dut)
    assert int(dut.busy.value) == 1, "Dispatcher retired while a block was still waiting"
    assert int(dut.done.value) == 0, "done rose with a block still waiting"

    # Core 3 takes the last block as soon as it is idle.
    dut.core_idle.value = 0b1000
    await Timer(1, unit="ns")
    expect_issue(dut, core=3, block_id=1)

    # Accept it, and keep that core busy so the job cannot retire yet.
    await RisingEdge(dut.clk)
    dut.core_idle.value = 0b0000
    await Timer(1, unit="ns")
    expect_idle_outputs(dut)
    assert int(dut.done.value) == 0, "done rose while the last core was still busy"

    dut.core_idle.value = 0b1111
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    assert int(dut.busy.value) == 0, "busy stayed high after the last core went idle"
    assert int(dut.done.value) == 1, "done did not rise after the last core went idle"


@cocotb.test()
async def test_dispatcher_reset(dut):
    """Verify an empty launch, a launch ignored while busy, and reset"""

    await start_clocked_dut(dut)

    # 1. block_count = 0 completes with no issue
    dut.core_idle.value = 0b1111
    await pulse_launch(dut, 0)
    expect_idle_outputs(dut)
    assert int(dut.busy.value) == 0, "Empty launch raised busy"
    assert int(dut.done.value) == 1, "Empty launch did not raise done"

    # 2. A second launch while busy does not replace the accepted block count
    dut.core_idle.value = 0b0010
    await pulse_launch(dut, 2)
    expect_issue(dut, core=1, block_id=0)

    await FallingEdge(dut.clk)
    dut.launch.value = 1
    dut.block_count.value = 9
    dut.core_idle.value = 0b0010
    await RisingEdge(dut.clk)
    dut.launch.value = 0
    await Timer(1, unit="ns")
    expect_issue(dut, core=1, block_id=1)

    # 3. Reset drops the in-flight job even if launch is still being presented
    dut.reset.value = 1
    dut.launch.value = 1
    dut.block_count.value = 4
    await Timer(1, unit="ns")
    expect_idle_outputs(dut)
    assert int(dut.busy.value) == 0, "Reset left busy set"
    assert int(dut.done.value) == 0, "Reset left done set"

    dut.launch.value = 0
    dut.reset.value = 0
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    expect_idle_outputs(dut)
    assert int(dut.busy.value) == 0, "Clearing reset started a job"
    assert int(dut.done.value) == 0, "Clearing reset raised done"
