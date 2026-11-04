`timescale 1ns/1ps
module tb_icore_systolic_2x2;
  reg clk=0,rst_n=0,start=0;
  reg [31:0] a_flat=0,b_flat=0;
  wire busy,done;
  wire [127:0] c_flat;
  reg [127:0] replay;
  reg signed [7:0] av,bv;
  reg signed [31:0] reference[0:3];
  integer i,j,k,t,n,seed=32'h00091911,pass_count=0,ssum;
  icore_systolic_2x2 dut(.*);
  always #5 clk=~clk;
  task load_case(input integer id);
    begin
      a_flat=0;b_flat=0;
      for(i=0;i<4;i=i+1)begin
        case(id)
          0:begin av=(i==0 || i==3)?8'sd1:8'sd0;bv=i+1;end // identity
          1:begin av=(i%2)?-128:127;bv=(i%2)?127:-128;end
          2:begin av=-128;bv=-128;end
          3:begin av=127;bv=127;end
          default:begin
            seed=(seed*32'd1664525)+32'd1013904223;
            av=$signed(seed[31:24]);
            seed=(seed*32'd1664525)+32'd1013904223;
            bv=$signed(seed[31:24]);
          end
        endcase
        a_flat[i*8 +: 8]=av;
        b_flat[i*8 +: 8]=bv;
      end
      for(i=0;i<2;i=i+1)
        for(j=0;j<2;j=j+1)begin
          ssum=0;
          for(k=0;k<2;k=k+1)begin
            av=$signed(a_flat[(i*2+k)*8 +: 8]);
            bv=$signed(b_flat[(k*2+j)*8 +: 8]);
            ssum=ssum+av*bv;
          end
          reference[i*2+j]=ssum;
        end
    end
  endtask
  task run_case(input integer id);
    begin
      @(negedge clk);load_case(id);start=1;
      @(negedge clk);start=0;
      if(!busy || done) $fatal(1,"start/busy protocol case=%0d",id);
      // Deliberately perturb external inputs and assert start while busy.
      a_flat=32'hFFFFFFFF;b_flat=32'h00000000;start=1;
      @(negedge clk);start=0;
      t=0;
      while(!done && t<8)begin @(negedge clk);t=t+1;end
      if(!done || busy || t!=4)$fatal(1,"latency contract case=%0d cycles=%0d",id,t);
      for(i=0;i<4;i=i+1)
        if($signed(c_flat[i*32 +: 32])!==reference[i])
          $fatal(1,"wrong result case=%0d idx=%0d actual=%0d expected=%0d",
            id,i,$signed(c_flat[i*32 +: 32]),reference[i]);
      pass_count=pass_count+1;
    end
  endtask
  initial begin
    repeat(3)@(negedge clk);rst_n=1;
    run_case(0);replay=c_flat;
    run_case(1);run_case(2);run_case(3);run_case(0);
    if(replay!==c_flat)$fatal(1,"Replay result drift");
    // Reset after a partially executed wavefront.
    @(negedge clk);load_case(3);start=1;
    @(negedge clk);start=0;
    repeat(2)@(negedge clk);
    rst_n=0;
    @(negedge clk);
    if(busy||done||c_flat!==0)$fatal(1,"reset abort failed");
    rst_n=1;
    run_case(3);
    for(n=0;n<256;n=n+1)run_case(1000+n);
    $display("PASS systolic_vectors=%0d randomized=256",pass_count);
    $display("ALL_SYSTOLIC_SIMULATION_TESTS_PASS");
    $finish;
  end
endmodule
