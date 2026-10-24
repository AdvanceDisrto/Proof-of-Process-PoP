`timescale 1ns/1ps
module ibare_core(
 input wire clk,input wire rst_n,input wire start,
 input wire [31:0] sequence_id,input wire [31:0] timestamp,
 input wire [31:0] telemetry_millijoules,input wire [255:0] framebuffer_hash,
 output reg ready,output reg [255:0] receipt
);
 localparam [255:0] DOMAIN=256'h6A09E667BB67AE853C6EF372A54FF53A510E527F9B05688C1F83D9AB5BE0CD19;
 reg [2:0] state;
 reg [255:0] mix;
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin state<=0;ready<=0;receipt<=0;mix<=0; end
  else case(state)
   0: begin ready<=0; if(start) state<=1; end
   1: begin mix<=framebuffer_hash; state<=2; end
   2: begin mix[31:0]<=mix[31:0]^sequence_id; mix[63:32]<=mix[63:32]^timestamp; state<=3; end
   3: begin mix[95:64]<=mix[95:64]^telemetry_millijoules; state<=4; end
   4: begin receipt<=mix^DOMAIN; state<=5; end
   5: begin ready<=1; state<=0; end
   default: state<=0;
  endcase
 end
endmodule
