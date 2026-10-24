module SPU_Systolic_Tensor_Core(input logic clk,input logic rst,input logic valid_i,input logic [31:0] a_i,b_i,output logic valid_o,output logic [31:0] y_o);
SPU_Sovereign_Core core(.clk(clk),.rst(rst),.valid_i(valid_i),.a_i(a_i),.b_i(b_i),.valid_o(valid_o),.y_o(y_o));
endmodule
