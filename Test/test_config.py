# ============================================================================
# File: Test/test_config.py
# Description: Centralized Path & Environment Configuration
# ============================================================================

import os
from pathlib import Path

# 1. Base directories
TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent

# 2. Source and include paths
SOURCE_DIR = PROJECT_ROOT / "Source"
INCLUDES_DIR = SOURCE_DIR / "Includes"
CORE_DIR = SOURCE_DIR / "Core"
MEMORY_DIR = SOURCE_DIR / "Memory"
TOP_DIR = SOURCE_DIR / "Top"

# Centralized list of include directories (corresponds to -I flags)
INCLUDE_PATHS = [INCLUDES_DIR]

# 3. Verilog source files per module
RTL_SOURCES = {
    "alu": [CORE_DIR / "alu.v"],
    "register_file": [CORE_DIR / "register_file.v"],
    "decoder": [CORE_DIR / "decoder.v"],
    "fetcher": [CORE_DIR / "fetcher.v"],
    "lsu": [CORE_DIR / "lsu.v"],
    "scheduler": [CORE_DIR / "scheduler.v"],
    "lane": [
        CORE_DIR / "alu.v",
        CORE_DIR / "register_file.v",
        CORE_DIR / "lsu.v",
        CORE_DIR / "lane.v",
    ],
    "core": [
        CORE_DIR / "alu.v",
        CORE_DIR / "register_file.v",
        CORE_DIR / "decoder.v",
        CORE_DIR / "lsu.v",
        CORE_DIR / "fetcher.v",
        CORE_DIR / "scheduler.v",
        CORE_DIR / "lane.v",
        CORE_DIR / "core.v",
    ],
    "memory_controller": [MEMORY_DIR / "memory_controller.v"],
    "dispatcher": [TOP_DIR / "dispatcher.v"],
    "gpu": [
        CORE_DIR / "alu.v",
        CORE_DIR / "register_file.v",
        CORE_DIR / "decoder.v",
        CORE_DIR / "lsu.v",
        CORE_DIR / "fetcher.v",
        CORE_DIR / "scheduler.v",
        CORE_DIR / "lane.v",
        CORE_DIR / "core.v",
        MEMORY_DIR / "memory_controller.v",
        TOP_DIR / "dispatcher.v",
        TOP_DIR / "gpu.v",
    ],
}

# 4. Directory containing test case modules (Test/Modules)
MODULES_DIR = TEST_DIR / "Modules"

# 5. Root directory for simulation build files and waveform output
SIM_BUILD_ROOT = PROJECT_ROOT / "sim_build"

# 6. Default simulator
DEFAULT_SIMULATOR = os.getenv("SIM", "icarus")

def get_sim_xml_path(toplevel_name: str) -> str:
    sim_dir = SIM_BUILD_ROOT / toplevel_name
    sim_dir.mkdir(parents=True, exist_ok=True)
    return str(sim_dir / f"{toplevel_name}_results.xml")
