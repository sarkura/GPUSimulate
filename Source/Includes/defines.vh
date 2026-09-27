// ============================================================================
// File: Source/Includes/defines.vh
// Description: Global definitions, macro parameters, and opcodes for Tiny-GPU.
// ============================================================================

`ifndef __DEFINES_VH__

`define __DEFINES_VH__

// ----------------------------------------------------------------------------
// 1. Data & Architecture Parameters
// ----------------------------------------------------------------------------
`define DATA_WIDTH      8       // Data width (8-bit)
`define ADDR_WIDTH      8       // Memory address width (8-bit)
`define REG_ADDR_WIDTH  3       // Register address width (3-bit, supports 8 registers R0~R7)
`define REG_NUM         8       // Total number of general-purpose registers



`define INST_WIDTH      16      // Instruction length (16-bit machine code)
//15      12 11       9 8        6 5        3 2         0
//┌──────────┬──────────┬──────────┬──────────┬──────────┐
//│  Opcode  │   Rdst   │  Rsrc1   │  Rsrc2   │ Reserved │
//│  (4-bit) │  (3-bit) │  (3-bit) │  (3-bit) │  (3-bit) │
//└──────────┴──────────┴──────────┴──────────┴──────────┘


// ----------------------------------------------------------------------------
// 2. ALU Operation Codes (4-bit)
// Used by the Decoder to pass the specific operation to the ALU
// ----------------------------------------------------------------------------
`define ALU_OP_WIDTH    4

`define ALU_NOP         4'b0000 // No Operation
`define ALU_ADD         4'b0001 // Addition: A + B
`define ALU_SUB         4'b0010 // Subtraction: A - B
`define ALU_MUL         4'b0011 // Multiplication: A * B
`define ALU_AND         4'b0100 // Bitwise AND: A & B
`define ALU_OR          4'b0101 // Bitwise OR: A | B
`define ALU_XOR         4'b0110 // Bitwise XOR: A ^ B
`define ALU_NOT         4'b0111 // Bitwise NOT: ~A
`define ALU_SHL         4'b1000 // Logical shift left: A << B
`define ALU_SHR         4'b1001 // Logical shift right: A >> B

// ----------------------------------------------------------------------------
// 3. Instruction Opcodes (upper 4 bits [15:12])
// Used for top-level machine code decoding
// ----------------------------------------------------------------------------
`define OPCODE_WIDTH    4

`define OP_NOP          4'b0000 // NOP: No operation
`define OP_ADD          4'b0001 // ADD: Register addition
`define OP_SUB          4'b0010 // SUB: Register subtraction
`define OP_MUL          4'b0011 // MUL: Register multiplication
`define OP_AND          4'b0100 // AND: Bitwise AND
`define OP_OR           4'b0101 // OR : Bitwise OR
`define OP_LDR          4'b1000 // LDR: Load data from memory into register
`define OP_STR          4'b1001 // STR: Store register data to memory
`define OP_BR           4'b1100 // BR : Conditional/unconditional branch
`define OP_HALT         4'b1111 // HALT: Halt/end of program

// ----------------------------------------------------------------------------
// 4. Memory Controller Command Codes (2-bit)
// ----------------------------------------------------------------------------
`define MEM_CMD_WIDTH   2

`define MEM_CMD_IDLE    2'b00   // Idle
`define MEM_CMD_READ    2'b01   // Memory read request
`define MEM_CMD_WRITE   2'b10   // Memory write request

`endif // __DEFINES_VH__
