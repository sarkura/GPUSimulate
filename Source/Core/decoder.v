// ============================================================================
// File: Source/Core/decoder.v
// Description: Instruction Decoder for Tiny-GPU
// ============================================================================

`timescale 1ns / 1ps

`include "defines.vh"
`include "config.vh"

module decoder (
    input  wire [`INST_WIDTH-1:0]     inst,         // 16-bit machine code

    output wire [`OPCODE_WIDTH-1:0]   opcode,       // Opcode field
    output wire [`REG_ADDR_WIDTH-1:0] rdst,         // Destination register
    output wire [`REG_ADDR_WIDTH-1:0] rsrc1,        // Source register 1
    output wire [`REG_ADDR_WIDTH-1:0] rsrc2,        // Source register 2

    output reg  [`ALU_OP_WIDTH-1:0]   alu_op,       // ALU opcode
    output reg                        reg_write_en, // Register write enable
    output reg  [`MEM_CMD_WIDTH-1:0]  mem_cmd,      // Memory command
    output reg                        branch,       // Branch request
    output reg                        halt          // Halt request
);

    // 1. Instruction field bounds, matching the layout in defines.vh
    //
    // 15      12 11       9 8        6 5        3 2         0
    // ┌──────────┬──────────┬──────────┬──────────┬──────────┐
    // │  Opcode  │   Rdst   │  Rsrc1   │  Rsrc2   │ Reserved │
    // └──────────┴──────────┴──────────┴──────────┴──────────┘
    localparam OPCODE_HI = `INST_WIDTH - 1;
    localparam OPCODE_LO = `INST_WIDTH - `OPCODE_WIDTH;
    localparam RDST_HI   = OPCODE_LO - 1;
    localparam RDST_LO   = RDST_HI - `REG_ADDR_WIDTH + 1;
    localparam RSRC1_HI  = RDST_LO - 1;
    localparam RSRC1_LO  = RSRC1_HI - `REG_ADDR_WIDTH + 1;
    localparam RSRC2_HI  = RSRC1_LO - 1;
    localparam RSRC2_LO  = RSRC2_HI - `REG_ADDR_WIDTH + 1;

    // 2. Field extract (combinational)
    //
    // ALU : Rdst <- Rsrc1 op Rsrc2
    // LDR : Rdst <- MEM[Rsrc1]
    // STR : MEM[Rsrc1] <- Rsrc2
    // Reserved [2:0] is ignored.
    assign opcode = inst[OPCODE_HI:OPCODE_LO];
    assign rdst   = inst[RDST_HI:RDST_LO];
    assign rsrc1  = inst[RSRC1_HI:RSRC1_LO];
    assign rsrc2  = inst[RSRC2_HI:RSRC2_LO];

    // 3. Control decode, matching opcodes defined in defines.vh
    //
    // Unlisted signals stay at the idle defaults below.
    always @(*) begin
        alu_op       = `ALU_NOP;
        reg_write_en = 1'b0;
        mem_cmd      = `MEM_CMD_IDLE;
        branch       = 1'b0;
        halt         = 1'b0;

        case (opcode)
            `OP_NOP: begin
            end
            `OP_ADD: begin
                alu_op       = `ALU_ADD;
                reg_write_en = 1'b1;
            end
            `OP_SUB: begin
                alu_op       = `ALU_SUB;
                reg_write_en = 1'b1;
            end
            `OP_MUL: begin
                alu_op       = `ALU_MUL;
                reg_write_en = 1'b1;
            end
            `OP_AND: begin
                alu_op       = `ALU_AND;
                reg_write_en = 1'b1;
            end
            `OP_OR: begin
                alu_op       = `ALU_OR;
                reg_write_en = 1'b1;
            end
            `OP_LDR: begin
                reg_write_en = 1'b1;
                mem_cmd      = `MEM_CMD_READ;
            end
            `OP_STR: begin
                mem_cmd      = `MEM_CMD_WRITE;
            end
            `OP_BR: begin
                branch       = 1'b1;
            end
            `OP_HALT: begin
                halt         = 1'b1;
            end
            default: begin
            end
        endcase
    end

endmodule
