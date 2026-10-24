`timescale 1ns/1ps
module raytracer_core(
 input wire clk,input wire rst_n,input wire render_trigger,
 output reg [7:0] pixel_out,output reg pixel_valid
);
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin pixel_out<=0;pixel_valid<=0; end
  else if(render_trigger) begin pixel_out<=8'hff;pixel_valid<=1; end
  else pixel_valid<=0;
 end
endmodule
