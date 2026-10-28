# Tiny-GPU

A small Verilog GPU used to study the datapath in [tiny-gpu](https://github.com/adam-maj/tiny-gpu). The block diagram and unit definitions live in [Docs/isa.md](Docs/isa.md). The bit-level instruction set lives in `Source/Includes/defines.vh`.

The machine is 8-bit. Each instruction is 16 bits. One core has four SIMD lanes. ALU and branch instructions finish in one clock. A memory instruction takes one clock per distinct address. Data memory is a 256-byte single-cycle SRAM.

## Design check

[Docs/isa.md](Docs/isa.md) describes two levels: one compute core, then a four-core GPU around it. The files below follow that split where a block has been written. Several blocks are still empty, and the written blocks are narrower than the diagram.

| Design block in `Docs/isa.md` | Current file | Result |
| --- | --- | --- |
| 1.3 Decoder | `Source/Core/decoder.v` | Matches the decode role. It splits the instruction and emits ALU, register-write, memory, branch, and halt controls. It does not score register dependencies. |
| 1.4.2 ALU | `Source/Core/alu.v` | Matches an integer ALU. It implements add, subtract, multiply, and, or, xor, not, and logical shifts, plus zero and signed overflow. There is no floating-point datapath. |
| 1.4.4 Register file | `Source/Core/register_file.v` | Matches a multi-ported register array for one lane: two combinational reads and one synchronous write. Eight 8-bit registers, cleared by reset. |
| 1.1 Intra-core scheduler | `Source/Core/scheduler.v` | Selects every lane that shares the lowest PC and is not halted. A memory instruction stays in that group until every selected lane has been served. There is no separate warp table beyond these four lanes. |
| 1.2 Fetcher | `Source/Core/fetcher.v` | Presents the scheduled PC and returns the instruction in the same cycle. There is no instruction cache and no multi-entry fetch buffer. |
| 1.4 SIMD lanes and control broadcast | `Source/Core/lane.v`, wired in `core.v` | Four lanes receive the same decoded controls. Each lane has its own PC, register file, ALU, and LSU. |
| 1.4.3 PC and write-back | `Source/Core/lane.v` | Sequential instructions increment the lane PC. `BR` loads it from that lane's `Rsrc1`. `HALT` freezes it. Write-back selects the ALU result or load data. |
| 1.4.1 LSU | `Source/Core/lsu.v` and the coalesce step in `core.v` | `LDR` is `Rdst <- MEM[Rsrc1]`. `STR` is `MEM[Rsrc1] <- Rsrc2`. Lanes that touch the same address share one memory transaction. |
| Core cache / external memory interface | — | Not written. The core data port is still one `mem_cmd`, `mem_addr`, `mem_wdata`, and `mem_rdata`. |
| 2.2 Dispatcher | `Source/Top/dispatcher.v` | Matches the top-level block scheduler for `CORE_NUM` cores (4). A launch carries a block count. Each cycle the lowest-numbered idle core receives the next block id. `done` rises after every block has been issued and every core is idle. It does not read MMIO registers itself, and it does not schedule warps inside a core. |
| 2.5 Memory controller | `Source/Memory/memory_controller.v` | Matches the core data port, not the two-channel DRAM controller in the diagram. One 256×8 memory. `READ` returns data in the same cycle. `WRITE` commits on the clock edge. No `ACTIVATE` sequence and no second channel. |
| 2.3 Core array | `Source/Top/gpu.v` | Four `core` instances. They share one instruction memory and one data memory. |
| 2.1 Device control registers | host ports on `gpu.v` | `launch`, `block_count`, `busy`, and `done`, plus host writes into instruction and data memory. There is no MMIO register block. |
| 2.4 Cache | — | Not written. Instructions sit in a 256-word SRAM in `gpu.v` with one read port per core. |
| 2.6 Interconnect | data arbiter in `gpu.v` | The lowest-numbered core with a data request owns the memory port for that cycle. Other requesting cores stall. |
| 2.7 PCIe / DMA | — | Not written. The testbench preloads memory through the host ports. |

`Source/Includes/config.vh` is reserved for project switches and is empty. The dispatcher still produces `block_id`, and the cores do not read it, so every block runs the same program.

## Instruction set

```
15      12 11       9 8        6 5        3 2         0
┌──────────┬──────────┬──────────┬──────────┬──────────┐
│  Opcode  │   Rdst   │  Rsrc1   │  Rsrc2   │ Reserved │
│  (4-bit) │  (3-bit) │  (3-bit) │  (3-bit) │  (3-bit) │
└──────────┴──────────┴──────────┴──────────┴──────────┘
```

The low 3 bits are ignored. `R0`–`R7` are general-purpose registers. `R0` is not hard-wired to zero. On reset, `R7` in a lane holds that lane's index (`0`–`3`). A program can overwrite `R7`.

| Opcode | Bits | Effect |
| --- | --- | --- |
| `NOP` | `0000` | No register write, no memory command, PC + 1 |
| `ADD` | `0001` | `Rdst <- Rsrc1 + Rsrc2` |
| `SUB` | `0010` | `Rdst <- Rsrc1 - Rsrc2` |
| `MUL` | `0011` | `Rdst <- Rsrc1 * Rsrc2`, low 8 bits |
| `AND` | `0100` | `Rdst <- Rsrc1 & Rsrc2` |
| `OR` | `0101` | `Rdst <- Rsrc1 \| Rsrc2` |
| `LDR` | `1000` | `Rdst <- MEM[Rsrc1]` |
| `STR` | `1001` | `MEM[Rsrc1] <- Rsrc2` |
| `BR` | `1100` | `PC <- Rsrc1` |
| `HALT` | `1111` | Freeze the PC and stop memory commands |

An undefined opcode behaves as `NOP`. The ALU also accepts xor, not, and shifts, but the instruction decoder never emits those operations.

Instruction memory and data memory are separate. The core fetches one 16-bit instruction per address and uses the data port only for `LDR` and `STR`.

## Dispatcher

`launch` is a one-cycle pulse and is sampled only while the dispatcher is idle. `block_count` is the number of blocks. Block ids are `0 .. block_count - 1`. A count of zero completes immediately.

`core_idle[i]` must be high for core `i` to receive work. A core that accepts `core_start` clears that bit on the same rising edge. `core_start` is one-hot. At most one block is issued per cycle. Reset clears a job in progress.

## Layout

```
Source/Includes/     defines.vh, config.vh
Source/Core/         scheduler, fetcher, decoder, lane, lsu, alu, register file, core
Source/Memory/       memory controller
Source/Top/          dispatcher, gpu
Docs/isa.md          block diagram and unit definitions
Test/test_runner.py  cocotb runner for RTL blocks
Test/Modules/        one test module per RTL block
Test/Utils/          golden_models.py, the NumPy matrices
Test/Software/       assembler.py, the standalone GPU matmul
```

## Matrix multiply

`Test/Utils/golden_models.py` holds one 4×4 sample. `matrix_a()` and `matrix_b()` return the inputs. `matrix_c()` returns `A @ B` as `uint8`, which is how the GPU's 8-bit multiply and add wrap. The sample values stay inside 0..255, so this is also the full integer product.

`Test/Software/assembler.py` loads that sample onto the GPU and is not part of `test_runner.py`. One block runs. The core does not receive `block_id`, so the four lanes inside that block do the parallel work, and `R7` selects the row:

| Address | Contents |
| --- | --- |
| `0` | Constant `1`, the value a lane can load through `R0` after reset |
| `16 .. 31` | `A`, row-major |
| `32 .. 47` | `B`, column-major, so one column is a contiguous walk of `+1` |
| `48 .. 63` | `C`, row-major, written by the lanes |

A second image in the same file runs the identical dot product on lane 0 only. Lanes 1..3 branch to `HALT`. Lane 0 repeats the row kernel with `BR`; the next PC comes from a table in data memory because the ISA has no conditional branch.

The value check compares both GPU images with `matrix_c()`. The time check reports GPU simulation cycles (a 10 ns clock) for the four-lane run and the one-lane run. It also prints the host wall-clock of one `matrix_c()` call. Those host microseconds are not the same unit as a simulated cycle.

From `Test/Software`, with mingw64 Python on the `PATH` and NumPy installed:

```bash
python assembler.py
```

## Tests

RTL tests use cocotb 2.x and Icarus Verilog. The checked environment is MSYS2 mingw64 (`C:\msys64\mingw64\bin` on the `PATH`).

From `Test`:

```bash
python test_runner.py
```

`test_runner.py` runs every suite in `test_all()`, from the ALU through the GPU top. A single suite can be started from Python, for example `test_runner.test_core()`. The matmul above stays outside that list.
