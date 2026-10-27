// ============================================================================
// File: Source/Core/scheduler.v
// Description: Lane scheduler for one Tiny-GPU compute core
// ============================================================================

`timescale 1ns / 1ps

`include "defines.vh"
`include "config.vh"

module scheduler (
    input  wire                              clk,
    input  wire                              reset,

    input  wire [`LANE_NUM*`ADDR_WIDTH-1:0]  lane_pc,
    input  wire [`LANE_NUM-1:0]              lane_halted,

    // Memory instructions retire one coalesced group per cycle.
    input  wire                              is_mem,
    input  wire [`LANE_NUM-1:0]              ack_mask,

    output wire [`ADDR_WIDTH-1:0]            issue_pc,
    output wire [`LANE_NUM-1:0]              exec_mask,
    output wire [`LANE_NUM-1:0]              serviced,
    output wire                              issue_valid,
    output wire                              retire
);

    // 1. Select every active lane that shares the lowest PC.
    //
    // Halted lanes are not eligible. Lanes with a different PC wait,
    // which is how a diverged branch rejoins later.
    wire [`ADDR_WIDTH-1:0] pc0 = lane_pc[`ADDR_WIDTH*1-1:`ADDR_WIDTH*0];
    wire [`ADDR_WIDTH-1:0] pc1 = lane_pc[`ADDR_WIDTH*2-1:`ADDR_WIDTH*1];
    wire [`ADDR_WIDTH-1:0] pc2 = lane_pc[`ADDR_WIDTH*3-1:`ADDR_WIDTH*2];
    wire [`ADDR_WIDTH-1:0] pc3 = lane_pc[`ADDR_WIDTH*4-1:`ADDR_WIDTH*3];

    reg [`ADDR_WIDTH-1:0] min_pc_c;
    reg [`LANE_NUM-1:0]   exec_mask_c;
    reg                   any_c;

    always @(*) begin
        any_c       = 1'b0;
        min_pc_c    = {`ADDR_WIDTH{1'b0}};
        exec_mask_c = {`LANE_NUM{1'b0}};

        if (!lane_halted[0]) begin
            any_c    = 1'b1;
            min_pc_c = pc0;
        end
        if (!lane_halted[1] && (!any_c || (pc1 < min_pc_c))) begin
            any_c    = 1'b1;
            min_pc_c = pc1;
        end
        if (!lane_halted[2] && (!any_c || (pc2 < min_pc_c))) begin
            any_c    = 1'b1;
            min_pc_c = pc2;
        end
        if (!lane_halted[3] && (!any_c || (pc3 < min_pc_c))) begin
            any_c    = 1'b1;
            min_pc_c = pc3;
        end

        if (any_c) begin
            if (!lane_halted[0] && (pc0 == min_pc_c)) exec_mask_c[0] = 1'b1;
            if (!lane_halted[1] && (pc1 == min_pc_c)) exec_mask_c[1] = 1'b1;
            if (!lane_halted[2] && (pc2 == min_pc_c)) exec_mask_c[2] = 1'b1;
            if (!lane_halted[3] && (pc3 == min_pc_c)) exec_mask_c[3] = 1'b1;
        end
    end

    assign issue_pc    = min_pc_c;
    assign exec_mask   = exec_mask_c;
    assign issue_valid = any_c;

    // 2. Hold the group until every selected lane has retired this instruction.
    //
    // ALU and branch instructions retire in the issue cycle.
    // A memory instruction retires after each distinct address has been issued.
    reg [`LANE_NUM-1:0] serviced_q;

    wire [`LANE_NUM-1:0] covered  = (serviced_q | ack_mask) & exec_mask_c;
    wire                 mem_done = (covered == exec_mask_c);

    assign serviced = serviced_q;
    assign retire   = issue_valid && (!is_mem || mem_done);

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            serviced_q <= {`LANE_NUM{1'b0}};
        end else if (!issue_valid || !is_mem || retire) begin
            serviced_q <= {`LANE_NUM{1'b0}};
        end else begin
            serviced_q <= covered;
        end
    end

endmodule
