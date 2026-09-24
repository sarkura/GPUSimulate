import os
from pathlib import Path
from cocotb_tools.runner import get_runner

def run_module_test(toplevel_name, sources, test_module_name):
    sim = os.getenv("SIM", "icarus")
    root_dir = Path(__file__).resolve().parent.parent

    runner = get_runner(sim)
    runner.build(
        verilog_sources = [root_dir / src for src in sources],
        hdl_toplevel = toplevel_name,
        includes = [root_dir / "src" / "includes"],
        always = True,
    )
    runner.test(
        hdl_toplevel = toplevel_name,
        test_module = test_module_name,
    )

#def test_all():
    #run_module_test("counter", ["counter.v"], "test_counter")

if __name__ == "__main__":
    #test_all()