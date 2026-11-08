`timescale 1ns/1ps
module tb_tessera_g;
  reg clk=0;
  always #5 clk=~clk;
  reg reset_n=0;
  reg cmd_valid=0;
  reg [1:0] cmd_verdict=0;
  reg [7:0] cmd_parent_a=8'hff;
  reg [7:0] cmd_parent_b=8'hff;
  wire cmd_ready;
  wire cmd_accepted;
  wire [2:0] cmd_state;
  wire [7:0] cmd_index;
  wire [7:0] node_count;
  wire overflow_seen;
  reg rd_valid=0;
  reg [7:0] rd_index=0;
  wire rd_exists;
  wire [2:0] rd_state;
  integer errors=0;
  integer checked=0;
  tessera_g_dag_tile #(.MAX_NODES(16), .IDX_W(8)) dut (
    .clk(clk), .reset_n(reset_n), .cmd_valid(cmd_valid),
    .cmd_ready(cmd_ready), .cmd_verdict(cmd_verdict),
    .cmd_parent_a(cmd_parent_a), .cmd_parent_b(cmd_parent_b),
    .cmd_accepted(cmd_accepted), .cmd_state(cmd_state),
    .cmd_index(cmd_index), .node_count(node_count),
    .overflow_seen(overflow_seen), .rd_valid(rd_valid),
    .rd_index(rd_index), .rd_exists(rd_exists), .rd_state(rd_state)
  );
  task append_node;
    input [1:0] verdict;
    input [7:0] pa;
    input [7:0] pb;
    input [2:0] expected;
    input [7:0] expected_index;
    begin
      @(negedge clk);
      cmd_verdict=verdict; cmd_parent_a=pa; cmd_parent_b=pb; cmd_valid=1;
      @(posedge clk); #1;
      checked=checked+1;
      if (cmd_accepted !== 1'b1 || cmd_state !== expected || cmd_index !== expected_index) begin
        errors=errors+1;
        $display("FAIL index=%0d expected=%0d got=%0d accepted=%0b",expected_index,expected,cmd_state,cmd_accepted);
      end
      $display("TRACE %0d %0d",cmd_index,cmd_state);
      @(negedge clk); cmd_valid=0;
    end
  endtask

  task check_read;
    input [7:0] index;
    input want_exist;
    input [2:0] want_status;
    begin
      rd_index=index; rd_valid=1; #1;
      checked=checked+1;
      if (rd_exists !== want_exist || rd_state !== want_status) begin
        errors=errors+1;
        $display("FAIL read=%0d exists=%0b status=%0d",index,rd_exists,rd_state);
      end
      rd_valid=0;
    end
  endtask
  initial begin
    repeat(3) @(negedge clk);
    reset_n=1;
    append_node(1,8'hff,8'hff,1, 0); // genesis
    append_node(1,0,8'hff,1, 1);    // valid child
    append_node(2,0,8'hff,2, 2);    // refuted child
    append_node(1,2,8'hff,3, 3);    // inherits blocked dependency
    append_node(1,0,1,1,4);         // valid two-parent DAG join
    append_node(1,4,2,3,5);         // one parent is refuted
    append_node(1,7,8'hff,5,6);     // future index invalid
    append_node(1,6,8'hff,3,7);     // descendant of invalid topology
    append_node(3,8'hff,8'hff,4,8);// unknown is NOT proven
    append_node(1,8,8'hff,3,9);     // descendant unknown blocked
    append_node(1,0,0,5,10);        // duplicate parents invalid
    append_node(1,0,12,5,11);       // future secondary parent invalid
    append_node(0,8'hff,8'hff,4,12);// uninitialized verdict => unknown
    append_node(2,8'hff,8'hff,2,13);// independent local refutation
    append_node(1,8'hff,8'hff,1,14);// independent valid
    append_node(1,14,8'hff,1,15);   // last valid slot
    if (node_count !== 8'd16 || cmd_ready !== 1'b0) begin
      errors=errors+1; $display("FAIL count and full");
    end
    checked=checked+1;
    check_read(0,1,1); check_read(3,1,3); check_read(10,1,5);
    check_read(15,1,1); check_read(16,0,0);
    @(negedge clk); cmd_valid=1;
    @(posedge clk); #1;
    checked=checked+1;
    if (cmd_accepted !== 0 || overflow_seen !== 1 || node_count !== 16) begin
      errors=errors+1; $display("FAIL overflow");
    end
    @(negedge clk); cmd_valid=0;
    reset_n=0; #1; checked=checked+1;
    if (node_count !== 0 || overflow_seen !== 0 || rd_exists !== 0) begin
      errors=errors+1; $display("FAIL reset");
    end
    reset_n=1;
    append_node(1,8'hff,8'hff,1,0);
    if(errors != 0) begin
       $display("TESSERA_G_RTL=FAIL checks=%0d errors=%0d",checked,errors);
       $fatal(1);
    end
    $display("TESSERA_G_RTL=PASS checks=%0d",checked);
    $finish;
  end
endmodule
