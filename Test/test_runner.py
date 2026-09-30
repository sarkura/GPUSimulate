# ============================================================================
# File: Test/test_runner.py
# Description: Modular Test Runner using cocotb 2.0+ Runner API & config
# ============================================================================

import sys
from cocotb_tools.runner import get_runner

# Import centralized configuration
import test_config as config

# Ensure Python can locate and import the test case files under Test/Modules
if str(config.TEST_DIR) not in sys.path:
    sys.path.append(str(config.TEST_DIR))


def run_module_test(toplevel_name, sources, test_module_name):
    """Generic module test dispatcher"""
    runner = get_runner(config.DEFAULT_SIMULATOR)
    build_dir = config.SIM_BUILD_ROOT / toplevel_name
    
    # 1. Compile Verilog RTL
    runner.build(
        sources=sources,
        hdl_toplevel=toplevel_name,
        includes=config.INCLUDE_PATHS,   # Include paths read from config
        always=True,
        build_dir=build_dir
    )

    # 2. Run Python Cocotb tests
    runner.test(
        hdl_toplevel=toplevel_name,
        test_module=test_module_name,
        test_dir=config.MODULES_DIR,     # Points to Test/Modules
        waves=True,
        results_xml=config.get_sim_xml_path(toplevel_name)
    )


def test_alu():
    """ALU test entry point"""
    run_module_test(
        toplevel_name="alu",
        sources=config.RTL_SOURCES["alu"],  # Source paths looked up in config by module name
        test_module_name="test_alu"
    )

def test_register_file():
    """Register file test entry point"""
    run_module_test(
        toplevel_name="register_file",
        sources=config.RTL_SOURCES["register_file"],  # Source paths looked up in config by module name
        test_module_name="test_register_file"
    )


def test_all():
    """Run all module tests"""
    test_alu()
    test_register_file()


if __name__ == "__main__":
    test_all()
