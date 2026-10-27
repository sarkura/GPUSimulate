// ============================================================================
// File: Source/Core/fetcher.v
// Description: Instruction fetch for one Tiny-GPU compute core
// ============================================================================

`timescale 1ns / 1ps

`include "defines.vh"
`include "config.vh"

module fetcher (
    input  wire [`ADDR_WIDTH-1:0] pc,        // PC selected by the scheduler
    input  wire                   fetch_en,  // Low while every lane is halted
    output wire [`ADDR_WIDTH-1:0] inst_addr, // Address presented to instruction memory
    input  wire [`INST_WIDTH-1:0] inst,      // Instruction returned the same cycle
    output wire [`INST_WIDTH-1:0] inst_out   // Instruction delivered to the decoder
);

    // Single-cycle instruction memory returns the word in the same cycle,
    // so the fetch buffer is the current response.
    assign inst_addr = pc;
    assign inst_out  = fetch_en ? inst : {`INST_WIDTH{1'b0}};

endmodule
