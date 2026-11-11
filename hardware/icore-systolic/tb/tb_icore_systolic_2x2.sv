`timescale 1ns/1ps
// iCore v0.3 regression: 2x2 output-stationary INT8 * INT8 -> INT32.
// Coverage: 32 corner, 16 skew, 4 immediate restarts, 4 reset/clean restarts,
// 512 seeded random, 1000 deterministic replays = 1568 checked executions.
// Independent integer golden model. NOT physical FPGA execution.
module tb_icore_systolic_2x2;
  reg clk=0,rst_n=0,start=0;
  reg [31:0] a_flat=0,b_flat=0;
  wire busy,done;
  wire [127:0] c_flat;
  reg [127:0] replay;
  reg signed [7:0] av,bv;
  reg signed [31:0] reference[0:3];
  reg [31:0] rng=32'h00091911;
  integer i,j,k,t,n,ssum;
  integer corner_count=0,skew_count=0,back_to_back_count=0;
  integer reset_count=0,random_count=0,replay_count=0;
  icore_systolic_2x2 dut(.*);
  always #5 clk=~clk;

  task calculate_reference;
    begin
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

  task load_case(input integer id);
    integer hot_a,hot_b;
    begin
      a_flat=0;b_flat=0;
      if (id>=100 && id<116) begin
        // Explicit wavefront-sensitive single-hot patterns.
        if (id<104) begin // single-hot A, B=identity
          hot_a=id-100;
          a_flat[hot_a*8 +: 8]=8'sd1;
          b_flat[0 +: 8]=8'sd1;
          b_flat[24 +: 8]=8'sd1;
        end else if (id<108) begin // A=identity, single-hot B
          hot_b=id-104;
          a_flat[0 +: 8]=8'sd1;
          a_flat[24 +: 8]=8'sd1;
          b_flat[hot_b*8 +: 8]=8'sd1;
        end else begin // paired A[i,k], B[k,j], both corners included
          hot_a=id-108;
          a_flat[((hot_a/4)*2 + (hot_a%2))*8 +: 8]=8'sd1;
          b_flat[(((hot_a%2)*2) + ((hot_a/2)%2))*8 +: 8]=-8'sd1;
        end
      end else if(id>=1000 && id<1512) begin
        for(i=0;i<4;i=i+1)begin
          rng=rng*32'd1664525+32'd1013904223;
          av=$signed(rng[31:24]);
          rng=rng*32'd1664525+32'd1013904223;
          bv=$signed(rng[31:24]);
          a_flat[i*8 +: 8]=av;
          b_flat[i*8 +: 8]=bv;
        end
      end else begin
        for(i=0;i<4;i=i+1)begin
          case(id)
            0:begin av=0;bv=0;end
            1:begin av=-128;bv=-128;end
            2:begin av=127;bv=127;end
            3:begin av=0;bv=127;end
            4:begin av=-128;bv=0;end
            5:begin av=(i==0 || i==3)?8'sd1:8'sd0;bv=i-2;end
            6:begin av=(i%2)?-128:127;bv=(i==0 || i==3)?8'sd1:8'sd0;end
            7:begin av=-128;bv=127;end
            8:begin av=127;bv=-128;end
            9:begin av=(i%2)?-128:127;bv=(i%2)?127:-128;end
            default:begin
              av=((id*11+i*37)%256)-128;
              bv=((id*17+i*13)%256)-128;
            end
          endcase
          a_flat[i*8 +: 8]=av;
          b_flat[i*8 +: 8]=bv;
        end
      end
      calculate_reference;
    end
  endtask

  task run_case(input integer id,input integer immediate_start);
    begin
      if(!immediate_start) @(negedge clk);
      load_case(id);start=1;
      @(negedge clk);start=0;
      if(!busy || done) $fatal(1,"start/busy protocol case=%0d",id);
      // Inputs may change while busy; another start must not overwrite state.
      a_flat=32'hFFFFFFFF;b_flat=32'h00000000;start=1;
      @(negedge clk);start=0;
      t=0;
      while(!done && t<8)begin @(negedge clk);t=t+1;end
      if(!done || busy || t!=4)$fatal(1,"latency contract case=%0d cycles=%0d",id,t);
      for(i=0;i<4;i=i+1)
        if($signed(c_flat[i*32 +: 32])!==reference[i])
          $fatal(1,"mismatch case=%0d elem=%0d actual=%0d expected=%0d",
            id,i,$signed(c_flat[i*32 +: 32]),reference[i]);
    end
  endtask

  task reset_during_wavefront(input integer phase);
    begin
      @(negedge clk);load_case(1);start=1;
      @(negedge clk);start=0;
      repeat(phase+1) @(negedge clk);
      if(!busy || done) $fatal(1,"not busy at reset phase=%0d",phase);
      rst_n=0;
      @(negedge clk);
      if(busy || done || c_flat!==0) $fatal(1,"reset abort phase=%0d failed",phase);
      rst_n=1;
      repeat(3)@(negedge clk);
      if(done) $fatal(1,"stale done phase=%0d",phase);
      run_case(5,0);
      reset_count=reset_count+1;
    end
  endtask

  initial begin
    repeat(3)@(negedge clk);rst_n=1;
    for(n=0;n<32;n=n+1)begin
      run_case(n,0);corner_count=corner_count+1;
    end
    $display("PASS corner_vectors=%0d",corner_count);
    for(n=100;n<116;n=n+1)begin
      run_case(n,0);skew_count=skew_count+1;
    end
    $display("PASS skew_vectors=%0d",skew_count);
    for(n=0;n<4;n=n+1)begin
      // Next start asserted at earliest next edge after previous 'done'.
      run_case(20+n,1);back_to_back_count=back_to_back_count+1;
    end
    $display("PASS back_to_back_vectors=%0d",back_to_back_count);
    for(n=0;n<4;n=n+1)reset_during_wavefront(n);
    $display("PASS mid_pipeline_resets=%0d",reset_count);
    for(n=1000;n<1512;n=n+1)begin
      run_case(n,0);random_count=random_count+1;
    end
    $display("PASS randomized_vectors=%0d seed=0x00091911",random_count);
    run_case(5,0);replay=c_flat;
    for(n=0;n<1000;n=n+1)begin
      run_case(5,0);
      if(c_flat!==replay)$fatal(1,"deterministic replay mismatch at n=%0d",n);
      replay_count=replay_count+1;
    end
    $display("PASS deterministic_replays=%0d",replay_count);
    if(corner_count!=32 || skew_count!=16 || back_to_back_count!=4 ||
      reset_count!=4 || random_count!=512 || replay_count!=1000)
      $fatal(1,"coverage counter mismatch");
    $display("ALL_SYSTOLIC_SIMULATION_TESTS_PASS total=%0d skew_scheme=output_stationary array=2x2 tiles_per_matmul=1",
      corner_count+skew_count+back_to_back_count+reset_count+random_count+replay_count);
    $finish;
  end
endmodule
