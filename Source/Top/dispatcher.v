// ============================================================================
// File: Source/Top/dispatcher.v
// Description: Block dispatcher for the Tiny-GPU core array
// ============================================================================

`timescale 1ns / 1ps

`include "defines.vh"
`include "config.vh"

module dispatcher (
    input  wire                        clk,
    input  wire                        reset,

    // Launch pulse from the device control registers.
    // Sampled only while the dispatcher is idle.
    input  wire                        launch,
    input  wire [`DATA_WIDTH-1:0]      block_count,

    // core_idle[i] is high when core i can accept a block.
    // A core that takes core_start must clear its idle bit on that rising edge.
    input  wire [`CORE_NUM-1:0]        core_idle,

    // One-hot start for the chosen core, valid in the cycle the block is offered.
    output wire [`CORE_NUM-1:0]        core_start,
    output wire [`DATA_WIDTH-1:0]      block_id,
    output wire                        busy,
    output wire                        done
);

    // 1. Job state. Block ids run from 0 to block_count - 1.
    reg                        busy_q;
    reg                        done_q;
    reg [`DATA_WIDTH-1:0]      next_block;
    reg [`DATA_WIDTH-1:0]      block_limit;

    assign busy = busy_q;
    assign done = done_q;

    // 2. Issue the next block to the lowest-numbered idle core.
    //
    // At most one core is started per cycle.
    // block_id and core_start stay at zero when nothing is issued.
    reg [`CORE_NUM-1:0]        core_start_c;
    reg [`DATA_WIDTH-1:0]      block_id_c;

    assign core_start = core_start_c;
    assign block_id   = block_id_c;

    always @(*) begin
        core_start_c = {`CORE_NUM{1'b0}};
        block_id_c   = {`DATA_WIDTH{1'b0}};

        if (busy_q && (next_block != block_limit) && (|core_idle)) begin
            block_id_c = next_block;
            if (core_idle[0])
                core_start_c[0] = 1'b1;
            else if (core_idle[1])
                core_start_c[1] = 1'b1;
            else if (core_idle[2])
                core_start_c[2] = 1'b1;
            else if (core_idle[3])
                core_start_c[3] = 1'b1;
        end
    end

    // 3. Accept a launch, count issued blocks, and retire the job.
    //
    // done rises once every block has been issued and every core is idle again.
    // Reset clears the job and wins over a launch on the same edge.
    wire issue = |core_start_c;

    always @(posedge clk or posedge reset) begin
        if (reset) begin
            busy_q      <= 1'b0;
            done_q      <= 1'b0;
            next_block  <= {`DATA_WIDTH{1'b0}};
            block_limit <= {`DATA_WIDTH{1'b0}};
        end else if (!busy_q && launch) begin
            next_block  <= {`DATA_WIDTH{1'b0}};
            block_limit <= block_count;
            if (block_count == {`DATA_WIDTH{1'b0}}) begin
                busy_q <= 1'b0;
                done_q <= 1'b1;
            end else begin
                busy_q <= 1'b1;
                done_q <= 1'b0;
            end
        end else if (busy_q) begin
            if (issue)
                next_block <= next_block + {{(`DATA_WIDTH-1){1'b0}}, 1'b1};
            if ((next_block == block_limit) && (&core_idle)) begin
                busy_q <= 1'b0;
                done_q <= 1'b1;
            end
        end
    end

endmodule
