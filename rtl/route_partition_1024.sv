module route_partition_1024(input logic clk,input logic rst,input logic valid_i,input logic [9:0] route_id_i,output logic valid_o,output logic [9:0] route_id_o);
always_ff @(posedge clk) begin
 if(rst) begin valid_o<=0; route_id_o<='0; end
 else begin valid_o<=valid_i; route_id_o<=route_id_i; end
end
endmodule
