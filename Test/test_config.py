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

# Centralized list of include directories (corresponds to -I flags)
INCLUDE_PATHS = [INCLUDES_DIR]

# 3. Verilog source files per module
RTL_SOURCES = {
    "alu": [CORE_DIR / "alu.v"],
    # Add new modules here:
    # "decoder": [CORE_DIR / "decoder.v"],
    # "register_file": [CORE_DIR / "register_file.v"],
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
