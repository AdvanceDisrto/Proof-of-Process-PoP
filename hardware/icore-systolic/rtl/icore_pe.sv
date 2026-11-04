// iCore iISA-0.2: signed INT8 multiply-accumulate processing element.
// Output-stationary accumulation, pipelined eastward A and southward B.
// This is digital, not photonic; no fabricated FPGA or hardware attestation.
module icore_pe #(
  parameter integer DW=8, AW=32
)(
  input wire clk, rst_n, clear,
  input wire signed [DW-1:0] a_in, b_in,
  input wire a_valid, b_valid,
  output reg signed [DW-1:0] a_east, b_south,
  output reg a_east_valid, b_south_valid,
  output reg signed [AW-1:0] acc
);
  wire signed [2*DW-1:0] product = a_in * b_in;
  wire signed [AW-1:0] product_ext =
    {{(AW-2*DW){product[2*DW-1]}},product};
  always @(posedge clk) begin
    if (!rst_n || clear) begin
      a_east<=0;b_south<=0;
      a_east_valid<=0;b_south_valid<=0;acc<=0;
    end else begin
      a_east<=a_in;b_south<=b_in;
      a_east_valid<=a_valid;b_south_valid<=b_valid;
      if(a_valid && b_valid)
        acc<=acc+product_ext;
    end
  end
endmodule
