// ============================================================================
// File: Source/Top/gpu.v
// Description: Four-core Tiny-GPU top
// ============================================================================

`timescale 1ns / 1ps

`include "defines.vh"
`include "config.vh"

module gpu (
    input  wire                        clk,
    input  wire                        reset,

    // Launch pulse. block_count is the number of blocks, ids 0 .. count-1.
    input  wire                        launch,
    input  wire [`DATA_WIDTH-1:0]      block_count,
    output wire                        busy,
    output wire                        done,

    // Host write port for the shared instruction memory.
    input  wire                        host_inst_we,
    input  wire [`ADDR_WIDTH-1:0]      host_inst_addr,
    input  wire [`INST_WIDTH-1:0]      host_inst_data,

    // Host port for the shared data memory. Used while the cores are idle.
    input  wire                        host_mem_we,
    input  wire                        host_mem_re,
    input  wire [`ADDR_WIDTH-1:0]      host_mem_addr,
    input  wire [`DATA_WIDTH-1:0]      host_mem_wdata,
    output wire [`DATA_WIDTH-1:0]      host_mem_rdata
);

    // 1. Instruction memory. Four cores read it in the same cycle.
    // Empty words are HALT, so a core that runs off the program stops.
    localparam IMEM_DEPTH = 1 << `ADDR_WIDTH;

    reg [`INST_WIDTH-1:0] imem [0:IMEM_DEPTH-1];

    integer ii;
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            for (ii = 0; ii < IMEM_DEPTH; ii = ii + 1)
                imem[ii] <= {`OP_HALT, {(`INST_WIDTH-`OPCODE_WIDTH){1'b0}}};
        end else if (host_inst_we) begin
            imem[host_inst_addr] <= host_inst_data;
        end
    end

    // 2. Dispatch one block at a time to the lowest-numbered idle core.
    wire [`CORE_NUM-1:0] core_idle;
    wire [`CORE_NUM-1:0] core_start;

    dispatcher u_dispatcher (
        .clk         (clk),
        .reset       (reset),
        .launch      (launch),
        .block_count (block_count),
        .core_idle   (core_idle),
        .core_start  (core_start),
        .block_id    (),
        .busy        (busy),
        .done        (done)
    );

    // 3. Four compute cores, sharing one data memory.
    wire [`ADDR_WIDTH-1:0]    core_pc       [0:`CORE_NUM-1];
    wire [`MEM_CMD_WIDTH-1:0] core_mem_cmd  [0:`CORE_NUM-1];
    wire [`ADDR_WIDTH-1:0]    core_mem_addr [0:`CORE_NUM-1];
    wire [`DATA_WIDTH-1:0]    core_mem_wdata[0:`CORE_NUM-1];
    wire [`CORE_NUM-1:0]      core_stall;
    wire [`DATA_WIDTH-1:0]    mem_rdata;

    genvar gi;
    generate
        for (gi = 0; gi < `CORE_NUM; gi = gi + 1) begin : g_core
            core u_core (
                .clk       (clk),
                .reset     (reset),
                .start     (core_start[gi]),
                .stall     (core_stall[gi]),
                .idle      (core_idle[gi]),
                .pc        (core_pc[gi]),
                .inst      (imem[core_pc[gi]]),
                .mem_cmd   (core_mem_cmd[gi]),
                .mem_addr  (core_mem_addr[gi]),
                .mem_wdata (core_mem_wdata[gi]),
                .mem_rdata (mem_rdata),
                .lane_pc   (),
                .halted    ()
            );
        end
    endgenerate

    // 4. Lowest-numbered requesting core owns the data port for this cycle.
    // The others hold retirement until they are granted.
    reg                      grant_valid;
    reg [1:0]                grant;
    reg [`MEM_CMD_WIDTH-1:0] grant_cmd;
    reg [`ADDR_WIDTH-1:0]    grant_addr;
    reg [`DATA_WIDTH-1:0]    grant_wdata;

    always @(*) begin
        grant_valid = 1'b0;
        grant       = 2'd0;
        grant_cmd   = `MEM_CMD_IDLE;
        grant_addr  = {`ADDR_WIDTH{1'b0}};
        grant_wdata = {`DATA_WIDTH{1'b0}};

        if (core_mem_cmd[0] != `MEM_CMD_IDLE) begin
            grant_valid = 1'b1;
            grant       = 2'd0;
            grant_cmd   = core_mem_cmd[0];
            grant_addr  = core_mem_addr[0];
            grant_wdata = core_mem_wdata[0];
        end else if (core_mem_cmd[1] != `MEM_CMD_IDLE) begin
            grant_valid = 1'b1;
            grant       = 2'd1;
            grant_cmd   = core_mem_cmd[1];
            grant_addr  = core_mem_addr[1];
            grant_wdata = core_mem_wdata[1];
        end else if (core_mem_cmd[2] != `MEM_CMD_IDLE) begin
            grant_valid = 1'b1;
            grant       = 2'd2;
            grant_cmd   = core_mem_cmd[2];
            grant_addr  = core_mem_addr[2];
            grant_wdata = core_mem_wdata[2];
        end else if (core_mem_cmd[3] != `MEM_CMD_IDLE) begin
            grant_valid = 1'b1;
            grant       = 2'd3;
            grant_cmd   = core_mem_cmd[3];
            grant_addr  = core_mem_addr[3];
            grant_wdata = core_mem_wdata[3];
        end
    end

    assign core_stall[0] = (core_mem_cmd[0] != `MEM_CMD_IDLE) && !(grant_valid && (grant == 2'd0));
    assign core_stall[1] = (core_mem_cmd[1] != `MEM_CMD_IDLE) && !(grant_valid && (grant == 2'd1));
    assign core_stall[2] = (core_mem_cmd[2] != `MEM_CMD_IDLE) && !(grant_valid && (grant == 2'd2));
    assign core_stall[3] = (core_mem_cmd[3] != `MEM_CMD_IDLE) && !(grant_valid && (grant == 2'd3));

    // 5. Data memory. A core request hides the host port for that cycle.
    wire [`MEM_CMD_WIDTH-1:0] mem_cmd  = grant_valid ? grant_cmd :
                                         host_mem_we ? `MEM_CMD_WRITE :
                                         host_mem_re ? `MEM_CMD_READ :
                                         `MEM_CMD_IDLE;
    wire [`ADDR_WIDTH-1:0]    mem_addr = grant_valid ? grant_addr : host_mem_addr;
    wire [`DATA_WIDTH-1:0]    mem_wdata = grant_valid ? grant_wdata : host_mem_wdata;

    memory_controller u_memory (
        .clk       (clk),
        .reset     (reset),
        .mem_cmd   (mem_cmd),
        .mem_addr  (mem_addr),
        .mem_wdata (mem_wdata),
        .mem_rdata (mem_rdata)
    );

    assign host_mem_rdata = mem_rdata;

endmodule
