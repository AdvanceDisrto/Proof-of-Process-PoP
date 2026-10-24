module SPU_Vector_Lane_4Wide(input logic clk, input logic rst, input logic valid_i, input logic [31:0] a_i, b_i, output logic valid_o, output logic [31:0] y_o);
always_ff @(posedge clk) begin
  if (rst) begin valid_o<=1'b0; y_o<='0; end
  else begin valid_o<=valid_i; y_o<=a_i+b_i; end
end
endmodule
