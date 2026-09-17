/*
 * Copyright (c) 2026 Rudra Joshi
 * SPDX-License-Identifier: Apache-2.0
 *
 * 8-bit wide, 16-deep synchronous FIFO, wrapped for Tiny Tapeout.
 */

`default_nettype none

// ---------------------------------------------------------------------------
// Tiny Tapeout wrapper. Pure wiring, no logic.
// ---------------------------------------------------------------------------
module tt_um_rj_fifo (
    input  wire [7:0] ui_in,    // dedicated inputs
    output wire [7:0] uo_out,   // dedicated outputs
    input  wire [7:0] uio_in,   // bidirectional: input path
    output wire [7:0] uio_out,  // bidirectional: output path
    output wire [7:0] uio_oe,   // bidirectional: 1 = drive out
    input  wire       ena,      // high while this design is selected
    input  wire       clk,
    input  wire       rst_n     // active low
);

    wire full;
    wire empty;

    // uio[1:0] are inputs  : wr_en, rd_en
    // uio[3:2] are outputs : full, empty
    // uio[7:4] unused, left as inputs
    assign uio_oe  = 8'b0000_1100;
    assign uio_out = {4'b0000, empty, full, 2'b00};

    fifo #(
        .WIDTH (8),
        .DEPTH (16)
    ) u_fifo (
        .clk     (clk),
        .rst_n   (rst_n),
        .wr_en   (uio_in[0]),
        .wr_data (ui_in),
        .rd_en   (uio_in[1]),
        .rd_data (uo_out),
        .full    (full),
        .empty   (empty)
    );

    // absorb unused inputs so the linter stays quiet
    wire _unused = &{ena, uio_in[7:2], 1'b0};

endmodule


// ---------------------------------------------------------------------------
// The FIFO itself.
// ---------------------------------------------------------------------------
module fifo #(
    parameter WIDTH = 8,
    parameter DEPTH = 16,
    parameter ADDR_W = $clog2(DEPTH)
) (
    input  wire             clk,
    input  wire             rst_n,
    input  wire             wr_en,
    input  wire [WIDTH-1:0] wr_data,
    input  wire             rd_en,
    output wire [WIDTH-1:0] rd_data,
    output wire             full,
    output wire             empty
);

    reg [WIDTH-1:0] mem [0:DEPTH-1];

    // one extra bit on each pointer distinguishes full from empty
    // at equal addresses, standard trick for a synchronous FIFO
    reg [ADDR_W:0] wr_ptr, rd_ptr;

    wire [ADDR_W-1:0] wr_addr = wr_ptr[ADDR_W-1:0];
    wire [ADDR_W-1:0] rd_addr = rd_ptr[ADDR_W-1:0];

    assign empty = (wr_ptr == rd_ptr);
    assign full  = (wr_ptr[ADDR_W] != rd_ptr[ADDR_W]) &&
                   (wr_ptr[ADDR_W-1:0] == rd_ptr[ADDR_W-1:0]);

    assign rd_data = mem[rd_addr];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr <= 0;
        end else if (wr_en && !full) begin
            mem[wr_addr] <= wr_data;
            wr_ptr <= wr_ptr + 1'b1;
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rd_ptr <= 0;
        end else if (rd_en && !empty) begin
            rd_ptr <= rd_ptr + 1'b1;
        end
    end

endmodule
