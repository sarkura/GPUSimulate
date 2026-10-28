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


def run_module_test(toplevel_name, sources, test_module_name, parameters=None):
    """Generic module test dispatcher"""
    runner = get_runner(config.DEFAULT_SIMULATOR)
    build_dir = config.SIM_BUILD_ROOT / toplevel_name
    
    # 1. Compile Verilog RTL
    runner.build(
        sources=sources,
        hdl_toplevel=toplevel_name,
        includes=config.INCLUDE_PATHS,   # Include paths read from config
        parameters=parameters or {},
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


def test_decoder():
    """Decoder test entry point"""
    run_module_test(
        toplevel_name="decoder",
        sources=config.RTL_SOURCES["decoder"],  # Source paths looked up in config by module name
        test_module_name="test_decoder"
    )


def test_fetcher():
    """Fetcher test entry point"""
    run_module_test(
        toplevel_name="fetcher",
        sources=config.RTL_SOURCES["fetcher"],  # Source paths looked up in config by module name
        test_module_name="test_fetcher"
    )


def test_lsu():
    """LSU test entry point"""
    run_module_test(
        toplevel_name="lsu",
        sources=config.RTL_SOURCES["lsu"],  # Source paths looked up in config by module name
        test_module_name="test_lsu"
    )


def test_scheduler():
    """Scheduler test entry point"""
    run_module_test(
        toplevel_name="scheduler",
        sources=config.RTL_SOURCES["scheduler"],  # Source paths looked up in config by module name
        test_module_name="test_scheduler"
    )


def test_lane():
    """Lane test entry point. LANE_ID is 3 so R7 resets to the lane index."""
    run_module_test(
        toplevel_name="lane",
        sources=config.RTL_SOURCES["lane"],  # Source paths looked up in config by module name
        test_module_name="test_lane",
        parameters={"LANE_ID": 3}
    )


def test_core():
    """Core test entry point"""
    run_module_test(
        toplevel_name="core",
        sources=config.RTL_SOURCES["core"],  # Source paths looked up in config by module name
        test_module_name="test_core"
    )


def test_memory_controller():
    """Memory controller test entry point"""
    run_module_test(
        toplevel_name="memory_controller",
        sources=config.RTL_SOURCES["memory_controller"],  # Source paths looked up in config by module name
        test_module_name="test_memory_controller"
    )


def test_dispatcher():
    """Dispatcher test entry point"""
    run_module_test(
        toplevel_name="dispatcher",
        sources=config.RTL_SOURCES["dispatcher"],  # Source paths looked up in config by module name
        test_module_name="test_dispatcher"
    )


def test_gpu():
    """GPU top test entry point"""
    run_module_test(
        toplevel_name="gpu",
        sources=config.RTL_SOURCES["gpu"],  # Source paths looked up in config by module name
        test_module_name="test_gpu"
    )


def test_all():
    """Run all module tests"""
    test_alu()
    test_register_file()
    test_decoder()
    test_fetcher()
    test_lsu()
    test_scheduler()
    test_lane()
    test_core()
    test_memory_controller()
    test_dispatcher()
    test_gpu()


if __name__ == "__main__":
    test_all()
