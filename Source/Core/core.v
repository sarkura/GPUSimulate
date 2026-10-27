// ============================================================================
// File: Source/Core/core.v
// Description: Four-lane compute core for Tiny-GPU
// ============================================================================

`timescale 1ns / 1ps

`include "defines.vh"
`include "config.vh"

module core (
    input  wire                              clk,
    input  wire                              reset,

    // Instruction port from the fetcher. One instruction per address.
    output wire [`ADDR_WIDTH-1:0]            pc,
    input  wire [`INST_WIDTH-1:0]            inst,

    // Coalesced data-memory port. One transaction per cycle.
    output wire [`MEM_CMD_WIDTH-1:0]         mem_cmd,
    output wire [`ADDR_WIDTH-1:0]            mem_addr,
    output wire [`DATA_WIDTH-1:0]            mem_wdata,
    input  wire [`DATA_WIDTH-1:0]            mem_rdata,

    output wire [`LANE_NUM*`ADDR_WIDTH-1:0]  lane_pc,
    output wire                              halted
);

    // 1. Lane state
    wire [`ADDR_WIDTH-1:0]    pc_l     [0:`LANE_NUM-1];
    wire                      halted_l [0:`LANE_NUM-1];
    wire                      req_valid_l [0:`LANE_NUM-1];
    wire [`MEM_CMD_WIDTH-1:0] req_cmd_l [0:`LANE_NUM-1];
    wire [`ADDR_WIDTH-1:0]    req_addr_l [0:`LANE_NUM-1];
    wire [`DATA_WIDTH-1:0]    req_wdata_l [0:`LANE_NUM-1];

    wire [`LANE_NUM*`ADDR_WIDTH-1:0] lane_pc_flat = {pc_l[3], pc_l[2], pc_l[1], pc_l[0]};
    wire [`LANE_NUM-1:0] lane_halted_flat = {halted_l[3], halted_l[2], halted_l[1], halted_l[0]};

    assign lane_pc = lane_pc_flat;
    assign halted  = &lane_halted_flat;

    // 2. Schedule the lanes that share the current PC
    wire [`ADDR_WIDTH-1:0] issue_pc;
    wire [`LANE_NUM-1:0]   exec_mask;
    wire [`LANE_NUM-1:0]   serviced;
    wire                   issue_valid;
    wire                   retire;
    wire                   is_mem;
    wire [`LANE_NUM-1:0]   ack_mask;

    scheduler u_scheduler (
        .clk         (clk),
        .reset       (reset),
        .lane_pc     (lane_pc_flat),
        .lane_halted (lane_halted_flat),
        .is_mem      (is_mem),
        .ack_mask    (ack_mask),
        .issue_pc    (issue_pc),
        .exec_mask   (exec_mask),
        .serviced    (serviced),
        .issue_valid (issue_valid),
        .retire      (retire)
    );

    // 3. Fetch the scheduled instruction.
    // After every lane halts, pc stays on lane 0 so the halt address remains visible.
    wire [`INST_WIDTH-1:0] fetched_inst;
    wire [`ADDR_WIDTH-1:0] fetch_pc = issue_valid ? issue_pc : pc_l[0];

    fetcher u_fetcher (
        .pc        (fetch_pc),
        .fetch_en  (issue_valid),
        .inst_addr (pc),
        .inst      (inst),
        .inst_out  (fetched_inst)
    );

    // 4. Decode, then broadcast the same controls to every lane
    wire [`REG_ADDR_WIDTH-1:0] rdst;
    wire [`REG_ADDR_WIDTH-1:0] rsrc1;
    wire [`REG_ADDR_WIDTH-1:0] rsrc2;
    wire [`ALU_OP_WIDTH-1:0]   alu_op;
    wire                       reg_write_en;
    wire [`MEM_CMD_WIDTH-1:0]  dec_mem_cmd;
    wire                       branch;
    wire                       dec_halt;

    decoder u_decoder (
        .inst         (fetched_inst),
        .opcode       (),
        .rdst         (rdst),
        .rsrc1        (rsrc1),
        .rsrc2        (rsrc2),
        .alu_op       (alu_op),
        .reg_write_en (reg_write_en),
        .mem_cmd      (dec_mem_cmd),
        .branch       (branch),
        .halt         (dec_halt)
    );

    assign is_mem = issue_valid && (dec_mem_cmd != `MEM_CMD_IDLE);

    // 5. Four lanes. R7 resets to the lane index.
    genvar gi;
    generate
        for (gi = 0; gi < `LANE_NUM; gi = gi + 1) begin : g_lane
            lane #(
                .LANE_ID(gi)
            ) u_lane (
                .clk          (clk),
                .reset        (reset),
                .exec_en      (exec_mask[gi]),
                .retire       (retire),
                .mem_ack      (ack_mask[gi]),
                .alu_op       (alu_op),
                .reg_write_en (reg_write_en),
                .mem_cmd      (dec_mem_cmd),
                .branch       (branch),
                .halt         (dec_halt),
                .rdst         (rdst),
                .rsrc1        (rsrc1),
                .rsrc2        (rsrc2),
                .mem_rdata    (mem_rdata),
                .pc           (pc_l[gi]),
                .halted       (halted_l[gi]),
                .req_valid    (req_valid_l[gi]),
                .req_cmd      (req_cmd_l[gi]),
                .req_addr     (req_addr_l[gi]),
                .req_wdata    (req_wdata_l[gi])
            );
        end
    endgenerate

    // 6. Coalesce lane requests onto one data-memory port.
    //
    // Lanes that still owe this instruction and share the lowest pending
    // address complete together. Different addresses take later cycles.
    wire [`LANE_NUM-1:0] pending = exec_mask & ~serviced & {
        req_valid_l[3], req_valid_l[2], req_valid_l[1], req_valid_l[0]
    };

    reg [1:0]                  pick;
    reg [`ADDR_WIDTH-1:0]      pick_addr;
    reg [`DATA_WIDTH-1:0]      pick_wdata;
    reg [`MEM_CMD_WIDTH-1:0]   pick_cmd;
    reg [`LANE_NUM-1:0]        ack_mask_c;

    always @(*) begin
        pick       = 2'd0;
        pick_addr  = {`ADDR_WIDTH{1'b0}};
        pick_wdata = {`DATA_WIDTH{1'b0}};
        pick_cmd   = `MEM_CMD_IDLE;
        ack_mask_c = {`LANE_NUM{1'b0}};

        if (is_mem && pending[0])
            pick = 2'd0;
        else if (is_mem && pending[1])
            pick = 2'd1;
        else if (is_mem && pending[2])
            pick = 2'd2;
        else if (is_mem && pending[3])
            pick = 2'd3;

        if (is_mem && (pending != {`LANE_NUM{1'b0}})) begin
            if (pick == 2'd0) begin
                pick_addr  = req_addr_l[0];
                pick_wdata = req_wdata_l[0];
                pick_cmd   = req_cmd_l[0];
            end else if (pick == 2'd1) begin
                pick_addr  = req_addr_l[1];
                pick_wdata = req_wdata_l[1];
                pick_cmd   = req_cmd_l[1];
            end else if (pick == 2'd2) begin
                pick_addr  = req_addr_l[2];
                pick_wdata = req_wdata_l[2];
                pick_cmd   = req_cmd_l[2];
            end else begin
                pick_addr  = req_addr_l[3];
                pick_wdata = req_wdata_l[3];
                pick_cmd   = req_cmd_l[3];
            end

            if (pending[0] && (req_addr_l[0] == pick_addr)) ack_mask_c[0] = 1'b1;
            if (pending[1] && (req_addr_l[1] == pick_addr)) ack_mask_c[1] = 1'b1;
            if (pending[2] && (req_addr_l[2] == pick_addr)) ack_mask_c[2] = 1'b1;
            if (pending[3] && (req_addr_l[3] == pick_addr)) ack_mask_c[3] = 1'b1;
        end
    end

    assign ack_mask  = ack_mask_c;
    assign mem_cmd   = pick_cmd;
    assign mem_addr  = pick_addr;
    assign mem_wdata = pick_wdata;

endmodule
