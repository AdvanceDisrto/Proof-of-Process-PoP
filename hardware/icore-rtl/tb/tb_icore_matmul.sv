`timescale 1ns/1ps
module tb_icore_matmul;
  localparam N=4,DW=8,AW=32;
  reg clk=0,rst_n=0,start=0;
  reg [N*N*DW-1:0] a_flat=0,b_flat=0;
  wire busy,done;
  wire [N*N*AW-1:0] c_flat;
  reg signed [AW-1:0] expected[0:N*N-1];
  integer i,j,k,t,sum;
  reg signed [DW-1:0] aa,bb;
  icore_matmul #(.N(N),.DW(DW),.AW(AW)) dut(.*);
  always #5 clk=~clk;
  task load_case(input integer which_case);
    begin
      a_flat=0;b_flat=0;
      for(i=0;i<N*N;i=i+1)begin
        case(which_case)
          0:begin aa=(i%5)-2;bb=((i*3)%7)-3;end
          1:begin aa=(i%2)?-128:127;bb=(i%3)?127:-128;end
          2:begin aa=(i%5)?0:1;bb=(i%5)?0:-1;end
          default:begin aa=((i*11+which_case)%255)-127;bb=((i*19+which_case)%255)-127;end
        endcase
        a_flat[i*DW +: DW]=aa;
        b_flat[i*DW +: DW]=bb;
      end
      for(i=0;i<N;i=i+1)
        for(j=0;j<N;j=j+1)begin
          sum=0;
          for(k=0;k<N;k=k+1)begin
            aa=$signed(a_flat[(i*N+k)*DW +: DW]);
            bb=$signed(b_flat[(k*N+j)*DW +: DW]);
            sum=sum+aa*bb;
          end
          expected[i*N+j]=sum;
        end
    end
  endtask
  task execute_and_check(input integer case_id);
    begin
      @(negedge clk);load_case(case_id);start=1;
      @(negedge clk);start=0;
      if(!busy || done)$fatal(1,"Handshake fail");
      a_flat={N*N*DW{1'b1}};b_flat=0;start=1;
      @(negedge clk);start=0;
      t=0;
      while(!done && t<N*N*N+4)begin @(negedge clk);t=t+1;end
      if(!done||busy)$fatal(1,"Completion timeout case=%0d",case_id);
      for(i=0;i<N*N;i=i+1)
        if($signed(c_flat[i*AW +: AW])!==expected[i])
          $fatal(1,"Mismatch case=%0d element=%0d actual=%0d expected=%0d",
            case_id,i,$signed(c_flat[i*AW +: AW]),expected[i]);
      $display("PASS case=%0d cycles=%0d",case_id,t);
    end
  endtask
  initial begin
    repeat(3)@(negedge clk);rst_n=1;
    execute_and_check(0);execute_and_check(1);execute_and_check(2);
    execute_and_check(3);execute_and_check(0);
    @(negedge clk);load_case(4);start=1;
    @(negedge clk);start=0;
    repeat(3)@(negedge clk);rst_n=0;
    @(negedge clk);
    if(busy||done||c_flat!==0)$fatal(1,"Reset fail");
    rst_n=1;execute_and_check(5);
    $display("ALL_RTL_SIMULATION_TESTS_PASS");$finish;
  end
endmodule
