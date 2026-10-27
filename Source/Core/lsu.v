// ============================================================================
// File: Source/Core/lsu.v
// Description: Per-lane load/store request for Tiny-GPU
// ============================================================================

`timescale 1ns / 1ps

`include "defines.vh"
`include "config.vh"

module lsu (
    input  wire                      exec_en,
    input  wire [`MEM_CMD_WIDTH-1:0] mem_cmd,
    input  wire [`DATA_WIDTH-1:0]    addr,       // Rsrc1
    input  wire [`DATA_WIDTH-1:0]    wdata,      // Rsrc2
    output wire                      req_valid,
    output wire [`MEM_CMD_WIDTH-1:0] req_cmd,
    output wire [`ADDR_WIDTH-1:0]    req_addr,
    output wire [`DATA_WIDTH-1:0]    req_wdata
);

    // LDR : addr = Rsrc1, data returns through the core write-back
    // STR : addr = Rsrc1, wdata = Rsrc2
    // The core coalesces lanes that touch the same address.
    assign req_valid = exec_en && (mem_cmd != `MEM_CMD_IDLE);
    assign req_cmd   = mem_cmd;
    assign req_addr  = addr;
    assign req_wdata = wdata;

endmodule
