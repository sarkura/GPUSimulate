GPU Summary


```
1.Core:


========================================================================================
                                     COMPUTE CORE
========================================================================================
                                          │
                                 [ External Memory / Cache ]
                                          │
                                          ▼ (1. Instruction Stream)
                          ┌──────────────────────────────┐
                          │   1.1 Scheduler              │
                          └──────────────┬───────────────┘
                                         │
                                         ▼
                          ┌──────────────────────────────┐
                          │    1.2 Fetcher               │
                          └──────────────┬───────────────┘
                                         │
                                         ▼ (Machine Code)
                          ┌──────────────────────────────┐
                          │    1.3 Decoder               │
                          └──────────────┬───────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   │ Control Signals Broadcast                 │
                   └──────┬───────────┬───────────┬────────────┘
                          │           │           │
                          ▼           ▼           ▼            ▼
========================================================================================
 1.4 Execution Lanes (SIMD Lanes - 1.4.1 ~ 1.4.4)
========================================================================================

    【 Lane 1 (1.4.1) 】    【 Lane 2 (1.4.2) 】    【 Lane 3 (1.4.3) 】    【 Lane 4 (1.4.4) 】
   ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
   │ 1.4.1.3 PC        │   │ 1.4.2.3 PC        │   │ 1.4.3.3 PC        │   │ 1.4.4.3 PC        │
   │ (Program Counter) │   │ (Program Counter) │   │ (Program Counter) │   │ (Program Counter) │
   └─────────┬─────────┘   └─────────┬─────────┘   └─────────┬─────────┘   └─────────┬─────────┘
             │                       │                       │                       │
             ▼                       ▼                       ▼                       ▼
   ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────┐
   │ 1.4.1.4 Register  │   │ 1.4.2.4 Register  │   │ 1.4.3.4 Register  │   │ 1.4.4.4 Register  │
   │ File              │   │ File              │   │ File              │   │ File              │
   └─────┬───────▲─────┘   └─────┬───────▲─────┘   └─────┬───────▲─────┘   └─────┬───────▲─────┘
         │       │               │       │               │       │               │       │
  (Read Data) (Write Back) (Read Data) (Write Back) (Read Data) (Write Back) (Read Data) (Write Back)
         │       │               │       │               │       │               │       │
    ┌────┴───────┴────┐     ┌────┴───────┴────┐     ┌────┴───────┴────┐     ┌────┴───────┴────┐
    │ 1.4.1.2 ALU     │     │ 1.4.2.2 ALU     │     │ 1.4.3.2 ALU     │     │ 1.4.4.2 ALU     │
    └─────────────────┘     └─────────────────┘     └─────────────────┘     └─────────────────┘
    ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
    │ 1.4.1.1 LSU     │     │ 1.4.2.1 LSU     │     │ 1.4.3.1 LSU     │     │ 1.4.4.1 LSU     │
    └────────┬────────┘     └────────┬────────┘     └────────┬────────┘     └────────┬────────┘
             │                       │                       │                       │
             └───────────────────────┴───────────┬───────────┴───────────────────────┘
                                                 │
                                                 ▼ (2. Parallel Data Access)
                                     [ External Memory / Cache ]


Reference:
    Scheduler / Task Scheduler
        Definition: The intra-core hardware engine responsible for warp/wavefront level instruction scheduling and thread management.
        Function: Tracks the operational state of active warps/threads, checks hazard conditions, and selects eligible warps to dispatch instructions each cycle to available execution pipelines.

    Fetcher (Instruction Fetch Unit / IFU)
        Definition: The hardware unit dedicated to retrieving raw instruction bitstreams into the core pipeline.
        Function: Issues fetch requests to the Instruction Cache using the active address stored in the Program Counter (PC) and queues raw machine code into instruction buffers.

    Decoder (Instruction Decoder / ID)
        Definition: The logic block that translates machine instructions into low-level control signals.
        Function: Parses opcode bit fields, identifies source/destination register addresses, detects execution dependency constraints, and generates micro-architectural control signals required by the execution pipelines.

    1.4 PC (Program Counter)
        Definition: A dedicated pointer register maintained per active warp or thread group.
        Function: Holds the memory address of the current or next instruction to be fetched, updating sequentially or jumping based on branch and control flow instructions.

    Register File (Register Array)
        Definition: The high-speed, multi-ported SRAM array residing directly inside the execution core.
        Function: Provides ultra-low-latency local storage for thread state and temporary variables. Multi-ported ports allow simultaneous read/write accesses across parallel execution lanes.

    Execution Lanes (SIMD Vector Lanes / Execution Pipelines)
        Definition: Parallel hardware execution pipelines operating under Single Instruction, Multiple Data (SIMD) or Single Instruction, Multiple Threads (SIMT) paradigms.
        Function: Executes identical control signals concurrently across multiple data channels, allowing independent threads within a warp to compute different data streams simultaneously.

    ALU (Arithmetic Logic Unit)
        Definition: The primary computational engine embedded within each execution lane.
        Function: Computes fundamental mathematical, logical, and bitwise operations (such as integer addition, floating-point fused multiply-add, shifts, and bitwise AND/OR).

    LSU (Load/Store Unit)
        Definition: The dedicated hardware block managing all memory transactions between registers and the memory hierarchy.
        Function: Calculates effective memory addresses generated by thread lanes, coalesces adjacent memory requests into unified memory transactions, and interfaces directly with local caches or external VRAM.

    Read Data / Write Back (Operand Read & Result Write-Back Stage)
        Definition: The datapath interface stages flanking the execution pipeline.
        Function: Operand Read retrieves input values from the Register File before execution; Write-Back commits computed results from ALUs/LSUs back to the destination registers upon completion.

    Control Signals Broadcast (Control Signal Distribution Unit)
        Definition: The internal distribution network for execution commands across the lane array.
        Function: Broadcasts decoded control signals uniformly across all parallel vector lanes in a single clock cycle, enforcing lock-step SIMD execution.

    External Memory / Cache Interface (L1 Data Cache & Shared Memory)
        Definition: The core-level memory interface connecting internal units to off-chip VRAM and local cache storage.
        Function: Serves instruction fetch and LSU data requests, handling cache hits locally while routing cache misses through the Interconnect Network to L2 cache or Memory Controllers.
```

```
2.GPU:


========================================================================================
                                      GPU SYSTEM (TOP)
========================================================================================
                                          │
                             [ Host CPU / PCIe Bus ]
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   │                                             │
                   ▼ (1. Command & Configuration)                ▼ (2. Host DMA Data Transfers)
  ┌─────────────────────────────────┐           ┌─────────────────────────────────┐
  │ 2.1 Device Control Registers    │           │ 2.7 PCIe / DMA Controller       │
  │ (MMIO / Control & Status Regs)  │           │ (Direct Memory Access Engine)   │
  └────────────────┬────────────────┘           └────────────────┬────────────────┘
                   │                                             │
                   ▼ (Start / Launch Signals)                    │
  ┌─────────────────────────────────┐                            │
  │ 2.2 Dispatcher                  │                            │
  │ (Thread / Block Scheduler)      │                            │
  └────────────────┬────────────────┘                            │
                   │                                             │
       ┌───────────┼───────────┬───────────┐                     │
       │ Task Distribution (Workgroup / Block Broadcast)         │
       │                                                         │
       ▼           ▼           ▼           ▼                     │
=================================================================│======================
 2.3 Compute Core Array (2.3.1 ~ 2.3.4)                          │
=================================================================│======================
  ┌──────────┐┌──────────┐┌──────────┐┌──────────┐               │
  │ 2.3.1    ││ 2.3.2    ││ 2.3.3    ││ 2.3.4    │               │
  │ Compute  ││ Compute  ││ Compute  ││ Compute  │               │
  │ Core 0   ││ Core 1   ││ Core 2   ││ Core 3   │               │
  └────┬─────┘└────┬─────┘└────┬─────┘└────┬─────┘               │
       │           │           │           │                     │
       └───────────┼───────────┴───────────┘                     │
                   │                                             │
                   ▼ (3. Core Memory Read/Write Requests)        │
  ┌──────────────────────────────────────────────────────────────┴────────────────┐
  │ 2.4 Cache                                                                     │
  │ (Shared L1 / L2 Data & Instruction Cache)                                     │
  └────────────────────────────────┬──────────────────────────────────────────────┘
                                   │
                                   ▼ (Traffic Routing)
  ┌───────────────────────────────────────────────────────────────────────────────┐
  │ 2.6 Interconnect / Crossbar Network                                           │
  │ (Address-Based Traffic Router & Arbiter)                                      │
  └─────────────────┬─────────────────────────────────────────┬───────────────────┘
                    │                                         │
                    ▼ (Channel 0 Traffic)                     ▼ (Channel 1 Traffic)
  ┌───────────────────────────────────┐     ┌───────────────────────────────────┐
  │ 2.5.1 Memory Controller 0         │     │ 2.5.2 Memory Controller 1         │
  │ (Channel 0 / VRAM Bank Group 0)   │     │ (Channel 1 / VRAM Bank Group 1)   │
  └─────────────────┬─────────────────┘     └─────────────────┬─────────────────┘
                    │                                         │
                    ▼ (4. Physical Memory Bus 0)              ▼ (5. Physical Memory Bus 1)
       [ External VRAM Channel 0 ]               [ External VRAM Channel 1 ]

Reference:
    Device Control Registers (MMIO / Control & Status Registers)
        Definition: Memory-Mapped I/O (MMIO) registers exposed directly to the Host CPU.
        Function: Stores configuration flags, kernel execution parameters (grid/block dimensions, instruction base addresses), and operational status flags (e.g., Start, Busy, Done). It triggers the Dispatcher upon receiving a launch command from the Host CPU.

    Dispatcher (Thread / Block Workload Dispatcher)
        Definition: The hardware task scheduling engine responsible for grid and workgroup distribution.
        Function: Accepts workload definitions from the Device Control Registers, monitors the execution availability of the Compute Core array, and dynamically dispatches thread blocks (or warps/wavefronts) to available cores.

    Compute Core Array (2.3.1 ~ 2.3.4 Streaming Multiprocessors / Compute Cores)
        Definition: The primary execution engines of the GPU, structured as an array of parallel cores.
        Function: Houses local instruction fetchers, decoders, execution lanes (ALUs, LSUs, Register Files, and Program Counters) to execute vector and scalar instructions in parallel.

    Cache (Shared On-Chip L1 / L2 Cache)
        Definition: High-speed, low-latency on-chip memory storage shared across execution units.
        Function: Caches frequently accessed instructions and dataset lines to minimize access latency to external VRAM. Intercepts read/write requests from Compute Cores and handles dirty cache line evictions.

    Memory Controllers (Multi-Channel VRAM Controllers)
        Definition: The physical memory interface engines managing distinct external VRAM channels.
        Function: Converts memory transactions from the Interconnect into physical DRAM command sequences (e.g., ACTIVATE, READ, WRITE). Multi-channel deployment multiplies memory bandwidth and mitigates bank collision stalls.

    Interconnect / Crossbar Network (On-Chip Traffic Router & Arbiter)
        Definition: A high-bandwidth, non-blocking crossbar routing matrix connecting on-chip requestors to memory targets.
        Function: Routes incoming memory requests from the PCIe/DMA Controller and Cache to the designated Memory Controller (0 or 1) based on physical address interleaving schemes.

    PCIe / DMA Controller (Direct Memory Access Engine)
        Definition: The high-speed bus interface controller linking the Host CPU to the internal GPU interconnect.
        Function: Handles Direct Memory Access (DMA) transactions, allowing the Host CPU to read from and write to external VRAM without burdening the Compute Cores.
```