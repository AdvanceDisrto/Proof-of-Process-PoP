`timescale 1ns/1ps
// iCore INT8xINT8->INT32 golden testbench.
// Covers six named cases, 1,000 seeded random cases, restart/replay,
// start-while-busy, latched input isolation, and reset at MAC #17.
// 63 counted negative-edge waits (64 MAC positive edges) is the v0.1 protocol.
module tb_icore_matmul;
  localparam integer N=4, DW=8, AW=32, EXPECTED_WAIT_CYCLES=N*N*N-1;
  localparam integer RANDOM_CASES=1000;
  reg clk=0, rst_n=0, start=0;
  reg [N*N*DW-1:0] a_flat=0, b_flat=0;
  wire busy,done;
  wire [N*N*AW-1:0] c_flat;
  reg signed [AW-1:0] expected[0:N*N-1];
  reg [N*N*AW-1:0] first_result;
  reg signed [DW-1:0] aa,bb;
  reg [31:0] rng=32'h1CE0_9115;
  integer i,j,k,t,sum,pass_count=0,n;
  icore_matmul #(.N(N),.DW(DW),.AW(AW)) dut(.*);
  always #5 clk=~clk;

  task load_case(input integer which_case);
    begin
      a_flat=0; b_flat=0;
      for(i=0;i<N*N;i=i+1) begin
        case(which_case)
          0:begin aa=(i%5)-2;bb=((i*3)%7)-3;end
          1:begin aa=(i%2)?-128:127;bb=(i%3)?127:-128;end
          2:begin aa=(i%5)?0:1;bb=(i%5)?0:-1;end
          3:begin aa=127;bb=127;end // max positive sum: 4*127*127
          4:begin aa=-128;bb=-128;end // max negative-input product: 4*128*128
          5:begin aa=(i%5)-2;bb=((i*3)%7)-3;end // deterministic replay of #0
          default:begin
            // Fixed-seed LCG, fully explicit sequence: reproducible in Icarus.
            rng=rng*32'd1664525 + 32'd1013904223;
            aa=$signed(rng[31:24]);
            rng=rng*32'd1664525 + 32'd1013904223;
            bb=$signed(rng[31:24]);
          end
        endcase
        a_flat[i*DW +: DW]=aa;
        b_flat[i*DW +: DW]=bb;
      end
      // Independent integer reference, not derived from DUT intermediate values.
      for(i=0;i<N;i=i+1)
        for(j=0;j<N;j=j+1) begin
          sum=0;
          for(k=0;k<N;k=k+1) begin
            aa=$signed(a_flat[(i*N+k)*DW +: DW]);
            bb=$signed(b_flat[(k*N+j)*DW +: DW]);
            sum=sum+(aa*bb);
          end
          expected[i*N+j]=sum;
        end
    end
  endtask

  task execute_and_check(input integer case_id, input integer verbose);
    begin
      @(negedge clk); load_case(case_id); start=1;
      @(negedge clk); start=0;
      if(!busy || done) $fatal(1,"Handshake fail case=%0d",case_id);
      // The core must use its latched operands and ignore a fresh start while busy.
      a_flat={N*N*DW{1'b1}}; b_flat=0; start=1;
      @(negedge clk); start=0;
      t=0;
      while(!done && t<N*N*N+4) begin @(negedge clk);t=t+1;end
      if(!done || busy) $fatal(1,"Completion timeout case=%0d",case_id);
      if(t!==EXPECTED_WAIT_CYCLES)
        $fatal(1,"Latency mismatch case=%0d cycles=%0d expected=%0d",case_id,t,EXPECTED_WAIT_CYCLES);
      for(i=0;i<N*N;i=i+1)
        if($signed(c_flat[i*AW +: AW])!==expected[i])
          $fatal(1,"Mismatch case=%0d element=%0d actual=%0d expected=%0d",
            case_id,i,$signed(c_flat[i*AW +: AW]),expected[i]);
      pass_count=pass_count+1;
      if(verbose) $display("PASS case=%0d cycles=%0d",case_id,t);
    end
  endtask

  initial begin
    repeat(3) @(negedge clk);
    rst_n=1;
    execute_and_check(0,1);
    first_result=c_flat;
    execute_and_check(1,1);
    execute_and_check(2,1);
    execute_and_check(3,1);
    execute_and_check(4,1);
    execute_and_check(5,1);
    if(c_flat!==first_result) $fatal(1,"Replay of case=0 is not bit-exact");

    // Reset must abort an in-flight result and prohibit a stale 'done'.
    @(negedge clk); load_case(4); start=1;
    @(negedge clk); start=0;
    repeat(17) @(negedge clk);
    if(!busy || done) $fatal(1,"Reset test did not reach busy state");
    rst_n=0;
    @(negedge clk);
    if(busy || done || c_flat!==0) $fatal(1,"Reset at MAC #17 failed");
    rst_n=1;
    repeat(4) @(negedge clk);
    if(done) $fatal(1,"Stale done after reset");
    execute_and_check(4,1);
    $display("PASS reset_at_mac17_and_restart");

    for(n=0;n<RANDOM_CASES;n=n+1)
      execute_and_check(1000+n,0);
    $display("PASS randomized_vectors=%0d seed=0x1CE09115",RANDOM_CASES);
    $display("ALL_RTL_SIMULATION_TESTS_PASS vectors=%0d expected_cycles=%0d",
             pass_count,EXPECTED_WAIT_CYCLES);
    $finish;
  end
endmodule
