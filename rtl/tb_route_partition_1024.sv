module tb;
logic clk=0,rst=1,valid_i=0,valid_o; logic [9:0] route_id_i,route_id_o;
always #5 clk=~clk;
route_partition_1024 dut(.*);
initial begin
 $dumpfile("route_tb.vcd"); $dumpvars(0,tb);
 repeat(2) @(posedge clk); rst<=0;
 @(posedge clk); valid_i<=1; route_id_i<=10'd0;
 @(posedge clk); #1 if(!valid_o||route_id_o!==10'd0) $fatal(1,"route 0 failed");
 @(posedge clk); route_id_i<=10'd1023;
 @(posedge clk); #1 if(!valid_o||route_id_o!==10'd1023) $fatal(1,"route 1023 failed");
 $display("[TB] RTL Simulation completed successfully."); $finish;
end
endmodule
