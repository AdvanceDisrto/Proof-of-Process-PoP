// iCore iISA-0.2: 2x2 output-stationary systolic matrix multiplier.
// Explicitly no opcode decoder yet. Fixed 2x2 for proof of the wavefront.
// A/B/C row-major signed INT8 x signed INT8 => INT32.
// A and B operands are latched on start, then edge-skewed across 2x2 PE mesh.
// Workload takes four wavefront MAC cycles and one drain cycle.
module icore_systolic_2x2 (
  input wire clk, rst_n, start,
  input wire [31:0] a_flat, b_flat,
  output reg busy, done,
  output wire [127:0] c_flat
);
  reg [31:0] a_reg,b_reg;
  reg [2:0] tick;
  wire signed [7:0] a00=a_reg[7:0], a01=a_reg[15:8];
  wire signed [7:0] a10=a_reg[23:16], a11=a_reg[31:24];
  wire signed [7:0] b00=b_reg[7:0], b01=b_reg[15:8];
  wire signed [7:0] b10=b_reg[23:16], b11=b_reg[31:24];
  wire signed [7:0] a_r0=(tick==0)?a00:(tick==1)?a01:8'sd0;
  wire signed [7:0] a_r1=(tick==1)?a10:(tick==2)?a11:8'sd0;
  wire signed [7:0] b_c0=(tick==0)?b00:(tick==1)?b10:8'sd0;
  wire signed [7:0] b_c1=(tick==1)?b01:(tick==2)?b11:8'sd0;
  wire va0=busy && (tick<=1);
  wire va1=busy && (tick>=1 && tick<=2);
  wire vb0=busy && (tick<=1);
  wire vb1=busy && (tick>=1 && tick<=2);
  wire clear=start && !busy;
  wire signed [7:0] a00_e, a10_e, b00_s, b01_s;
  wire va00_e,va10_e,vb00_s,vb01_s;
  wire signed [31:0] c00,c01,c10,c11;
  icore_pe pe00(.clk(clk),.rst_n(rst_n),.clear(clear),
    .a_in(a_r0),.b_in(b_c0),.a_valid(va0),.b_valid(vb0),
    .a_east(a00_e),.b_south(b00_s),
    .a_east_valid(va00_e),.b_south_valid(vb00_s),.acc(c00));
  icore_pe pe01(.clk(clk),.rst_n(rst_n),.clear(clear),
    .a_in(a00_e),.b_in(b_c1),.a_valid(va00_e),.b_valid(vb1),
    .a_east(),.b_south(b01_s),
    .a_east_valid(),.b_south_valid(vb01_s),.acc(c01));
  icore_pe pe10(.clk(clk),.rst_n(rst_n),.clear(clear),
    .a_in(a_r1),.b_in(b00_s),.a_valid(va1),.b_valid(vb00_s),
    .a_east(a10_e),.b_south(),
    .a_east_valid(va10_e),.b_south_valid(),.acc(c10));
  icore_pe pe11(.clk(clk),.rst_n(rst_n),.clear(clear),
    .a_in(a10_e),.b_in(b01_s),.a_valid(va10_e),.b_valid(vb01_s),
    .a_east(),.b_south(),.a_east_valid(),.b_south_valid(),.acc(c11));
  assign c_flat={c11,c10,c01,c00};
  always @(posedge clk) begin
    if(!rst_n) begin
      a_reg<=0;b_reg<=0;tick<=0;busy<=0;done<=0;
    end else if(start && !busy) begin
      a_reg<=a_flat;b_reg<=b_flat;tick<=0;busy<=1;done<=0;
    end else if(busy) begin
      if(tick==4) begin busy<=0;done<=1;end
      else tick<=tick+1'b1;
    end
  end
endmodule
