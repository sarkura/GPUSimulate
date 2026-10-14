// ============================================================================
// File: Source/Memory/memory_controller.v
// Description: Single-cycle data memory for Tiny-GPU
// ============================================================================

`timescale 1ns / 1ps

`include "defines.vh"
`include "config.vh"

module memory_controller (
    input  wire                      clk,
    input  wire                      reset,

    // Data port, matching the core memory interface.
    input  wire [`MEM_CMD_WIDTH-1:0] mem_cmd,
    input  wire [`ADDR_WIDTH-1:0]    mem_addr,
    input  wire [`DATA_WIDTH-1:0]    mem_wdata,
    output wire [`DATA_WIDTH-1:0]    mem_rdata
);

    // 1. Storage. One byte at each of the 256 addresses.
    localparam MEM_DEPTH = 1 << `ADDR_WIDTH;

    reg [`DATA_WIDTH-1:0] mem [0:MEM_DEPTH-1];

    // 2. Combinational read
    //
    // LDR needs mem_rdata in the same cycle as the request.
    // IDLE and WRITE drive zeros so a read is the only command that returns data.
    assign mem_rdata = (mem_cmd == `MEM_CMD_READ) ? mem[mem_addr]
                                                  : {`DATA_WIDTH{1'b0}};

    // 3. Synchronous write
    //
    // STR commits mem_wdata on the rising edge.
    // Reset clears every location and wins over a write on the same edge.
    integer i;
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            for (i = 0; i < MEM_DEPTH; i = i + 1) begin
                mem[i] <= {`DATA_WIDTH{1'b0}};
            end
        end else if (mem_cmd == `MEM_CMD_WRITE) begin
            mem[mem_addr] <= mem_wdata;
        end
    end

endmodule
