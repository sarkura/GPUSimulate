// ============================================================================
// File: Source/Core/core.v
// Description: Single-cycle compute core for Tiny-GPU
// ============================================================================

`timescale 1ns / 1ps

`include "defines.vh"
`include "config.vh"

module core (
    input  wire                      clk,
    input  wire                      reset,

    // Instruction port. One instruction is fetched per address.
    output wire [`ADDR_WIDTH-1:0]    pc,
    input  wire [`INST_WIDTH-1:0]    inst,

    // Data memory port
    output wire [`MEM_CMD_WIDTH-1:0] mem_cmd,
    output wire [`ADDR_WIDTH-1:0]    mem_addr,
    output wire [`DATA_WIDTH-1:0]    mem_wdata,
    input  wire [`DATA_WIDTH-1:0]    mem_rdata,

    output wire                      halted
);

    // 1. Program counter and halt
    //
    // Sequential instructions advance pc by 1.
    // BR  writes pc with Rsrc1.
    // HALT freezes pc until reset.
    reg [`ADDR_WIDTH-1:0] pc_q;
    reg                   halted_q;

    assign pc     = pc_q;
    assign halted = halted_q;

    // 2. Decode
    wire [`REG_ADDR_WIDTH-1:0] rdst;
    wire [`REG_ADDR_WIDTH-1:0] rsrc1;
    wire [`REG_ADDR_WIDTH-1:0] rsrc2;
    wire [`ALU_OP_WIDTH-1:0]   alu_op;
    wire                       dec_reg_write_en;
    wire [`MEM_CMD_WIDTH-1:0]  dec_mem_cmd;
    wire                       dec_branch;
    wire                       dec_halt;

    decoder u_decoder (
        .inst         (inst),
        .opcode       (),
        .rdst         (rdst),
        .rsrc1        (rsrc1),
        .rsrc2        (rsrc2),
        .alu_op       (alu_op),
        .reg_write_en (dec_reg_write_en),
        .mem_cmd      (dec_mem_cmd),
        .branch       (dec_branch),
        .halt         (dec_halt)
    );

    // 3. Register read
    //
    // Port A is Rsrc1 (ALU operand A, load/store address, branch target).
    // Port B is Rsrc2 (ALU operand B, store data).
    wire [`DATA_WIDTH-1:0] rs1_data;
    wire [`DATA_WIDTH-1:0] rs2_data;
    wire [`DATA_WIDTH-1:0] wb_data;
    wire                   rf_write_en;

    register_file u_register_file (
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

    // 4. ALU
    wire [`DATA_WIDTH-1:0] alu_result;

    alu u_alu (
        .a        (rs1_data),
        .b        (rs2_data),
        .alu_op   (alu_op),
        .result   (alu_result),
        .zero     (),
        .overflow ()
    );

    // 5. Data memory request
    //
    // LDR : Rdst <- MEM[Rsrc1]
    // STR : MEM[Rsrc1] <- Rsrc2
    assign mem_cmd   = halted_q ? `MEM_CMD_IDLE : dec_mem_cmd;
    assign mem_addr  = rs1_data;
    assign mem_wdata = rs2_data;

    // 6. Write-back. A load selects memory data; every other write selects the ALU.
    assign wb_data     = (dec_mem_cmd == `MEM_CMD_READ) ? mem_rdata : alu_result;
    assign rf_write_en = dec_reg_write_en & ~halted_q;

    // 7. Control transfer
    always @(posedge clk or posedge reset) begin
        if (reset) begin
            pc_q     <= {`ADDR_WIDTH{1'b0}};
            halted_q <= 1'b0;
        end else if (!halted_q) begin
            if (dec_halt) begin
                halted_q <= 1'b1;
            end else if (dec_branch) begin
                pc_q <= rs1_data;
            end else begin
                pc_q <= pc_q + {{(`ADDR_WIDTH-1){1'b0}}, 1'b1};
            end
        end
    end

endmodule
