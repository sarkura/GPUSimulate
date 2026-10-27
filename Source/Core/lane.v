// ============================================================================
// File: Source/Core/lane.v
// Description: One SIMD lane: PC, register file, ALU, and LSU
// ============================================================================

`timescale 1ns / 1ps

`include "defines.vh"
`include "config.vh"

module lane #(
    parameter [`DATA_WIDTH-1:0] LANE_ID = {`DATA_WIDTH{1'b0}}
) (
    input  wire                        clk,
    input  wire                        reset,

    // Broadcast controls. exec_en qualifies this lane for the current PC.
    input  wire                        exec_en,
    input  wire                        retire,
    input  wire                        mem_ack,
    input  wire [`ALU_OP_WIDTH-1:0]    alu_op,
    input  wire                        reg_write_en,
    input  wire [`MEM_CMD_WIDTH-1:0]   mem_cmd,
    input  wire                        branch,
    input  wire                        halt,
    input  wire [`REG_ADDR_WIDTH-1:0]  rdst,
    input  wire [`REG_ADDR_WIDTH-1:0]  rsrc1,
    input  wire [`REG_ADDR_WIDTH-1:0]  rsrc2,
    input  wire [`DATA_WIDTH-1:0]      mem_rdata,

    output wire [`ADDR_WIDTH-1:0]      pc,
    output wire                        halted,
    output wire                        req_valid,
    output wire [`MEM_CMD_WIDTH-1:0]   req_cmd,
    output wire [`ADDR_WIDTH-1:0]      req_addr,
    output wire [`DATA_WIDTH-1:0]      req_wdata
);

    // 1. Program counter. Reset starts every lane at address 0.
    reg [`ADDR_WIDTH-1:0] pc_q;
    reg                   halted_q;

    assign pc     = pc_q;
    assign halted = halted_q;

    // 2. Register file. R7 resets to this lane's index.
    wire [`DATA_WIDTH-1:0] rs1_data;
    wire [`DATA_WIDTH-1:0] rs2_data;
    wire [`DATA_WIDTH-1:0] alu_result;
    wire                   is_load = (mem_cmd == `MEM_CMD_READ);
    wire                   is_mem  = (mem_cmd != `MEM_CMD_IDLE);
    wire [`DATA_WIDTH-1:0] wb_data = is_load ? mem_rdata : alu_result;
    wire                   rf_write_en = !halted_q && reg_write_en &&
                          (is_load ? (exec_en && mem_ack) : (exec_en && !is_mem));

    register_file #(
        .RESET_R7(LANE_ID)
    ) u_register_file (
        .clk         (clk),
        .reset       (reset),
        .read_addr_a (rsrc1),
        .read_data_a (rs1_data),
        .read_addr_b (rsrc2),
        .read_data_b (rs2_data),
        .write_addr  (rdst),
        .write_data  (wb_data),
        .write_en    (rf_write_en)
    );

    // 3. ALU
    alu u_alu (
        .a        (rs1_data),
        .b        (rs2_data),
        .alu_op   (alu_op),
        .result   (alu_result),
        .zero     (),
        .overflow ()
    );

    // 4. Load/store request
    lsu u_lsu (
        .exec_en   (exec_en && !halted_q),
        .mem_cmd   (mem_cmd),
        .addr      (rs1_data),
        .wdata     (rs2_data),
        .req_valid (req_valid),
        .req_cmd   (req_cmd),
        .req_addr  (req_addr),
        .req_wdata (req_wdata)
    );

    // 5. PC update. Memory instructions wait until the whole group retires.
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            pc_q     <= {`ADDR_WIDTH{1'b0}};
            halted_q <= 1'b0;
        end else if (exec_en && retire && !halted_q) begin
            if (halt) begin
                halted_q <= 1'b1;
            end else if (branch) begin
                pc_q <= rs1_data;
            end else begin
                pc_q <= pc_q + {{(`ADDR_WIDTH-1){1'b0}}, 1'b1};
            end
        end
    end

endmodule
