import os
from pathlib import Path
from cocotb_tools.runner import get_runner

def test_counter():
    sim = os.getenv("SIM", "icarus")
    proj_path = Path(__file__).resolve().parent

    sources = [proj_path / "counter.v"]

    # get the runner instance for the corresponding simulator (icarus)
    runner = get_runner(sim)
    
    # compile Verilog source code
    runner.build(
        verilog_sources=sources,
        hdl_toplevel="counter",
        always=True,
    )

    # run Python cocotb test
    runner.test(
        hdl_toplevel="counter",
        test_module="test_counter",
    )

if __name__ == "__main__":
    test_counter()