// ============================================================================
// File: Source/Core/alu.v
// Description: Arithmetic Logic Unit for Tiny-GPU
// ============================================================================

`timescale 1ns / 1ps

`include "defines.vh"
`include "config.vh"

module alu (
    input  wire [`DATA_WIDTH-1:0] a,        // Operand A
    input  wire [`DATA_WIDTH-1:0] b,        // Operand B
    input  wire [`ALU_OP_WIDTH-1:0] alu_op, // ALU opcode (4-bit)
    output reg  [`DATA_WIDTH-1:0] result,   // Result (8-bit)
    output wire                   zero,     // Zero flag
    output wire                   overflow  // Signed overflow flag for ADD/SUB
);

    // 1. Most significant bit index (MSB = 7)
    localparam MSB = `DATA_WIDTH - 1;

    // 2. Zero flag (set when result is all zeros)
    assign zero = (result == {`DATA_WIDTH{1'b0}});

    // 3. Overflow flag (valid only for signed ADD / SUB)
    wire is_add = (alu_op == `ALU_ADD);
    wire is_sub = (alu_op == `ALU_SUB);
    assign overflow = (is_add && (a[MSB] == b[MSB]) && (result[MSB] != a[MSB])) ||
                      (is_sub && (a[MSB] != b[MSB]) && (result[MSB] != a[MSB]));

    // 4. ALU decode logic, matching opcodes defined in defines.vh
    always @(*) begin
        case (alu_op)
            `ALU_NOP: result = {`DATA_WIDTH{1'b0}};
            `ALU_ADD: result = a + b;
            `ALU_SUB: result = a - b;
            `ALU_MUL: result = a * b;             // 8-bit multiply, truncated to low 8 bits
            `ALU_AND: result = a & b;
            `ALU_OR : result = a | b;
            `ALU_XOR: result = a ^ b;
            `ALU_NOT: result = ~a;                 // Unary bitwise NOT
            `ALU_SHL: result = a << b[2:0];        // Logical shift A left by B[2:0] bits
            `ALU_SHR: result = a >> b[2:0];        // Logical shift A right by B[2:0] bits
            default:  result = {`DATA_WIDTH{1'b0}};
        endcase
    end

endmodule
