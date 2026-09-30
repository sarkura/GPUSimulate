// ============================================================================
// File: Source/Core/register_file.v
// Description: Arithmetic Logic Unit for Tiny-GPU
// ============================================================================
`timescale 1ns / 1ps

`include "defines.vh"
`include "config.vh"

module register_file (
    input  wire clk,
    input  wire reset,

    // Read Port A
    input  wire [`REG_ADDR_WIDTH-1:0] read_addr_a,
    output wire [`DATA_WIDTH-1:0] read_data_a,

    // Read Port B
    input  wire [`REG_ADDR_WIDTH-1:0] read_addr_b,
    output wire [`DATA_WIDTH-1:0] read_data_b,

    // Write Port
    input  wire [`REG_ADDR_WIDTH-1:0] write_addr,
    input  wire [`DATA_WIDTH-1:0] write_data,
    input  wire write_en
);

    // ============================================================
    // 1. Register Storage
    // ============================================================

    reg [`DATA_WIDTH-1:0] registers [0:`REG_NUM-1];

    // ============================================================
    // 2. Read Logic
    // ============================================================
    //
    // Register file uses combinational/asynchronous read.
    // Changing the read address directly changes the read data.
    //

    assign read_data_a = registers[read_addr_a];
    assign read_data_b = registers[read_addr_b];


    // ============================================================
    // 3. Write Logic
    // ============================================================
    //
    // Register writes happen on the rising edge of clk.
    //

    integer i;
    always @(posedge clk or posedge reset) begin

        if (reset) begin

            // Clear all registers.
            for (i = 0; i < `REG_NUM; i = i + 1) begin
                registers[i] <= {`DATA_WIDTH{1'b0}};
            end

        end else if (write_en) begin

            // Write data into selected register.
            registers[write_addr] <= write_data;

        end

    end

endmodule
