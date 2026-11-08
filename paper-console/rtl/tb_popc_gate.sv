`timescale 1ns/1ps
module tb_popc_gate;
  reg clk=0; always #5 clk=~clk;
  reg reset_n=0,cmd_valid=0;
  reg [7:0] flags=8'hff;
  reg [255:0] digest=256'h123456789abcdef;
  wire processed,sign_request,reject;
  wire [7:0] fail_mask;
  wire [255:0] output_hash;
  integer checks=0, failures=0,bit_idx;
  popc_gate dut(.clk(clk),.reset_n(reset_n),.cmd_valid(cmd_valid),
    .math_verified(flags[7]),.meter_fresh(flags[6]),
    .meter_calibrated(flags[5]),.energy_in_range(flags[4]),
    .thermal_ok(flags[3]),.signer_ready(flags[2]),
    .consent(flags[1]),.source_attested(flags[0]),
    .claim_sha256(digest),.processed(processed),.sign_request(sign_request),
    .reject(reject),.fail_mask(fail_mask),.permitted_claim_sha256(output_hash));
  task check;
    input should_sign;
    input [7:0] mask;
    begin
      @(negedge clk);cmd_valid=1;
      @(posedge clk);#1;
      checks=checks+1;
      if(processed!==1 || sign_request!==should_sign || reject===should_sign ||
         fail_mask!==mask || (should_sign && output_hash!==digest) ||
         (!should_sign && output_hash!==0))begin
        failures=failures+1;$display("FAIL flags=%h sign=%b rejected=%b mask=%h",flags,sign_request,reject,fail_mask);
      end
      @(negedge clk);cmd_valid=0;
      @(posedge clk);#1;
      checks=checks+1;
      if (sign_request!==0 || processed!==0)begin
         failures=failures+1;$display("FAIL pulse didn't end");
      end
    end
  endtask
  initial begin
    repeat(3)@(negedge clk);reset_n=1;
    check(1,0);
    for(bit_idx=0;bit_idx<8;bit_idx=bit_idx+1)begin
      flags=8'hff ^ (8'h1<<bit_idx);
      check(0,8'h1<<bit_idx);
    end
    flags=8'hff; digest=0;check(0,0);digest=256'h01234;
    flags=8'h00;check(0,8'hff);
    reset_n=0;#1; checks=checks+1;
    if(sign_request!==0 || output_hash!==0 || fail_mask!==8'hff)failures=failures+1;
    reset_n=1;flags=8'hff;check(1,0);
    if(failures!=0)begin
       $display("POPC_GATE_SIM=FAIL checks=%0d errors=%0d",checks,failures);$fatal(1);
    end
    $display("POPC_GATE_SIM=PASS checks=%0d",checks);$finish;
  end
endmodule
