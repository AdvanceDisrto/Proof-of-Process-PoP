`timescale 1ns / 1ps
// Board-level simulation ONLY: synthetic verdicts, no actual FPGA programming.
module tb_tessera_g_arty_top;
    reg clk100 = 0;
    always #5 clk100 = ~clk100;
    reg btn_reset = 1;
    wire [3:0] led;
    wire rgb0_r, rgb0_g, rgb0_b;
    integer test_count = 0;

    tessera_g_arty_top dut (
        .clk100(clk100), .btn_reset(btn_reset), .led(led),
        .rgb0_r(rgb0_r), .rgb0_g(rgb0_g), .rgb0_b(rgb0_b)
    );

    task check_completed;
        begin
            repeat (24) @(negedge clk100);
            test_count = test_count + 1;
            if (led !== 4'b1111 || rgb0_g !== 1'b1 ||
                rgb0_r !== 1'b0 || rgb0_b !== 1'b0) begin
                $display("FAIL: board visual state led=%b rgb=%b%b%b",
                         led, rgb0_r, rgb0_g, rgb0_b);
                $fatal(1);
            end
        end
    endtask

    initial begin
        repeat (4) @(negedge clk100);
        btn_reset = 0;
        check_completed();
        btn_reset = 1;
        repeat (3) @(negedge clk100);
        test_count = test_count + 1;
        if (led !== 4'b0000 || rgb0_g !== 1'b0) begin
            $display("FAIL: button reset didn't clear visual state");
            $fatal(1);
        end
        btn_reset = 0;
        check_completed();
        $display("TESSERA_ARTY_BOARD_SIM=PASS checks=%0d visual=all_four_leds_plus_green_rgb",
                 test_count);
        $finish;
    end
endmodule
