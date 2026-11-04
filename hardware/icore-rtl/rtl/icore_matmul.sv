// iISA-0.1: sequential signed INT8 4x4 matrix multiply, INT32 result.
// Row-major flattened operands; lowest element in least significant bits.
// This RTL does not establish FPGA implementation or fabricated silicon.
module icore_matmul #(
  parameter integer N=4, DW=8, AW=32
)(
  input wire clk, rst_n, start,
  input wire [N*N*DW-1:0] a_flat, b_flat,
  output reg busy, done,
  output reg [N*N*AW-1:0] c_flat
);
  localparam integer IW = N<=1 ? 1 : $clog2(N);
  reg [IW-1:0] row, col, k;
  reg signed [AW-1:0] acc;
  reg [N*N*DW-1:0] a_reg, b_reg;
  wire signed [DW-1:0] ae = a_reg[(row*N+k)*DW +: DW];
  wire signed [DW-1:0] be = b_reg[(k*N+col)*DW +: DW];
  wire signed [2*DW-1:0] product = ae * be;
  wire signed [AW-1:0] sum = acc + {{(AW-2*DW){product[2*DW-1]}}, product};
  always @(posedge clk) begin
    if (!rst_n) begin
      row<=0;col<=0;k<=0;acc<=0;a_reg<=0;b_reg<=0;
      c_flat<=0;busy<=0;done<=0;
    end else if (start && !busy) begin
      a_reg<=a_flat;b_reg<=b_flat;c_flat<=0;
      row<=0;col<=0;k<=0;acc<=0;busy<=1;done<=0;
    end else if (busy) begin
      if (k==N-1) begin
        c_flat[(row*N+col)*AW +: AW] <= sum;
        acc<=0;k<=0;
        if (col==N-1) begin
          col<=0;
          if (row==N-1) begin row<=0;busy<=0;done<=1;end
          else row<=row+1'b1;
        end else col<=col+1'b1;
      end else begin
        acc<=sum;k<=k+1'b1;
      end
    end
  end
endmodule
