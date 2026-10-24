module tb_ispu10240;
logic clk=0,rst=1,valid_i=0,valid_o; logic [31:0] a_i,b_i,y_o;
always #5 clk=~clk;
SPU_Sovereign_10240_Lock dut(.clk(clk),.rst(rst),.valid_i(valid_i),.a_i(a_i),.b_i(b_i),.valid_o(valid_o),.y_o(y_o));
initial begin
 $dumpfile("ispu10240_tb.vcd"); $dumpvars(0,tb_ispu10240);
 repeat(2) @(posedge clk); rst<=0;
 @(posedge clk); valid_i<=1; a_i<=32'd40; b_i<=32'd2;
 @(posedge clk); #1 if(!valid_o || y_o!==32'd42) $fatal(1,"iSPU vector path failed");
 $display("[TB] iSPU10240 locked hierarchy PASS"); $finish;
end
endmodule
