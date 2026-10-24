`timescale 1ns/1ps
module tb_ibare_system;
 reg clk=0,rst_n=0,start=0; reg [31:0] seq=1,ts=1711210000,mj=425;
 reg [255:0] fb; wire ready; wire [255:0] receipt;
 ibare_core uut(.clk(clk),.rst_n(rst_n),.start(start),.sequence_id(seq),.timestamp(ts),
  .telemetry_millijoules(mj),.framebuffer_hash(fb),.ready(ready),.receipt(receipt));
 always #5 clk=~clk;
 initial begin
  if(!$value$plusargs("FB_HASH=%h",fb))
   fb=256'hA3F9C2E1D4B8A7F6E5D2C1B0A9F8E7D6C5B4A3F2E1D0C9B8A7F6E5D4C3B2A1F0;
  #10 rst_n=1; #10 start=1; #10 start=0;
  @(posedge ready); $display("RTL_RECEIPT=%h",receipt); $finish;
 end
endmodule
