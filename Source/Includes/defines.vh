// ============================================================================
// File: Source/Includes/defines.vh
// Description: Global definitions, macro parameters, and opcodes for Tiny-GPU.
// ============================================================================

`ifndef __DEFINES_VH__

`define __DEFINES_VH__

// ----------------------------------------------------------------------------
// 1. Data & Architecture Parameters (架构位宽与宏定义)
// ----------------------------------------------------------------------------
`define DATA_WIDTH      8       // 数据位宽 (8-bit)
`define ADDR_WIDTH      8       // 内存地址位宽 (8-bit)
`define REG_ADDR_WIDTH  3       // 寄存器寻址位宽 (3-bit, 支持 R0~R7 共 8 个寄存器)
`define REG_NUM         8       // 通用寄存器总数



`define INST_WIDTH      16      // 指令长度 (16-bit 机器码)
//15      12 11       9 8        6 5        3 2         0
//┌──────────┬──────────┬──────────┬──────────┬──────────┐
//│  Opcode  │   Rdst   │  Rsrc1   │  Rsrc2   │ Reserved │
//│  (4-bit) │  (3-bit) │  (3-bit) │  (3-bit) │  (3-bit) │
//└──────────┴──────────┴──────────┴──────────┴──────────┘


// ----------------------------------------------------------------------------
// 2. ALU Operation Codes (ALU 操作码定义 - 4-bit)
// 用于 Decoder 向 ALU 传递具体的计算指令
// ----------------------------------------------------------------------------
`define ALU_OP_WIDTH    4

`define ALU_NOP         4'b0000 // 空操作 (No Operation)
`define ALU_ADD         4'b0001 // 加法: A + B
`define ALU_SUB         4'b0010 // 减法: A - B
`define ALU_MUL         4'b0011 // 乘法: A * B
`define ALU_AND         4'b0100 // 按位与: A & B
`define ALU_OR          4'b0101 // 按位或: A | B
`define ALU_XOR         4'b0110 // 按位异或: A ^ B
`define ALU_NOT         4'b0111 // 按位取反: ~A
`define ALU_SHL         4'b1000 // 逻辑左移: A << B
`define ALU_SHR         4'b1001 // 逻辑右移: A >> B

// ----------------------------------------------------------------------------
// 3. Instruction Opcodes (指令集操作码 - 高 4 位 [15:12])
// 机器码顶层译码使用
// ----------------------------------------------------------------------------
`define OPCODE_WIDTH    4

`define OP_NOP          4'b0000 // NOP: 无操作
`define OP_ADD          4'b0001 // ADD: 寄存器加法
`define OP_SUB          4'b0010 // SUB: 寄存器减法
`define OP_MUL          4'b0011 // MUL: 寄存器乘法
`define OP_AND          4'b0100 // AND: 按位与
`define OP_OR           4'b0101 // OR : 按位或
`define OP_LDR          4'b1000 // LDR: 从内存加载数据到寄存器 (Load)
`define OP_STR          4'b1001 // STR: 将寄存器数据保存到内存 (Store)
`define OP_BR           4'b1100 // BR : 条件/无条件跳转 (Branch)
`define OP_HALT         4'b1111 // HALT: 停机/结束指令

// ----------------------------------------------------------------------------
// 4. Memory Controller Command Codes (内存控制器命令码 - 2-bit)
// ----------------------------------------------------------------------------
`define MEM_CMD_WIDTH   2

`define MEM_CMD_IDLE    2'b00   // 空闲状态
`define MEM_CMD_READ    2'b01   // 内存读请求
`define MEM_CMD_WRITE   2'b10   // 内存写请求

`endif // __DEFINES_VH__