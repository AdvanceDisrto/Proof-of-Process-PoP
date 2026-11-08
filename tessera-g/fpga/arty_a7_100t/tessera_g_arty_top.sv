// SPDX-License-Identifier: Apache-2.0
// iNNOVULIS Tessera-G Arty A7-100T board demonstration.
// Only exercises deterministic locally generated, synthetic DAG states.
// GREEN LED does NOT certify external math, signatures, sensors, or facts.
module tessera_g_arty_top (
    input wire clk100,
    input wire btn_reset,
    output wire [3:0] led,
    output wire rgb0_r,
    output wire rgb0_g,
    output wire rgb0_b
);
    localparam [1:0] ISSUE = 2'd0, CHECK = 2'd1, VERIFY = 2'd2, DONE = 2'd3;

    // Asynchronous assertion, synchronous release. FPGA INIT boot state is demo-only.
    (* ASYNC_REG = "TRUE" *) reg [1:0] rst_pipe = 2'b00;
    always @(posedge clk100 or posedge btn_reset) begin
        if (btn_reset) rst_pipe <= 2'b00;
        else rst_pipe <= {rst_pipe[0], 1'b1};
    end
    wire reset_n = rst_pipe[1];

    reg [1:0] phase;
    reg [2:0] step;
    reg error_seen;
    reg [3:0] steps_passed;
    reg [3:0] readback_passed;
    reg [1:0] scan_idx;

    wire cmd_valid = (phase == ISSUE);
    wire cmd_ready;
    wire cmd_accepted;
    wire [2:0] cmd_state;
    wire [7:0] cmd_index;
    wire [7:0] node_count;
    wire overflow_seen;
    wire rd_exists;
    wire [2:0] rd_state;
    wire [7:0] rd_index = {6'd0, scan_idx};
    wire [2:0] expected_read = (scan_idx == 2'd1) ? 3'd2 :
                               (scan_idx == 2'd2) ? 3'd3 : 3'd1;

    reg [1:0] cmd_verdict;
    reg [7:0] cmd_parent_a;
    reg [2:0] expected_state;
    always @* begin
        cmd_verdict = 2'd1;
        cmd_parent_a = 8'hff;
        expected_state = 3'd1;
        case (step)
            3'd0: begin // Genesis, declared locally OK.
                cmd_verdict = 2'd1; cmd_parent_a = 8'hff; expected_state = 3'd1;
            end
            3'd1: begin // Rogue locally refuted.
                cmd_verdict = 2'd2; cmd_parent_a = 8'd0; expected_state = 3'd2;
            end
            3'd2: begin // Positive claim blocked by refuted ancestor.
                cmd_verdict = 2'd1; cmd_parent_a = 8'd1; expected_state = 3'd3;
            end
            3'd3: begin // Independent valid sibling of rogue.
                cmd_verdict = 2'd1; cmd_parent_a = 8'd0; expected_state = 3'd1;
            end
            default: begin
                cmd_verdict = 2'd0; cmd_parent_a = 8'hff; expected_state = 3'd4;
            end
        endcase
    end

    tessera_g_dag_tile #(.MAX_NODES(16), .IDX_W(8)) tile (
        .clk(clk100), .reset_n(reset_n),
        .cmd_valid(cmd_valid), .cmd_ready(cmd_ready),
        .cmd_verdict(cmd_verdict), .cmd_parent_a(cmd_parent_a),
        .cmd_parent_b(8'hff), .cmd_accepted(cmd_accepted),
        .cmd_state(cmd_state), .cmd_index(cmd_index),
        .node_count(node_count), .overflow_seen(overflow_seen),
        .rd_valid(phase == VERIFY), .rd_index(rd_index),
        .rd_exists(rd_exists), .rd_state(rd_state)
    );

    always @(posedge clk100 or negedge reset_n) begin
        if (!reset_n) begin
            phase <= ISSUE;
            step <= 3'd0;
            error_seen <= 1'b0;
            steps_passed <= 4'd0;
            readback_passed <= 4'd0;
            scan_idx <= 2'd0;
        end else begin
            case (phase)
                ISSUE: begin
                    if (cmd_ready) phase <= CHECK;
                    else begin error_seen <= 1'b1; phase <= DONE; end
                end
                CHECK: begin
                    if (cmd_accepted && cmd_index == {5'd0,step} &&
                        cmd_state == expected_state && !overflow_seen) begin
                        steps_passed[step[1:0]] <= 1'b1;
                        if (step == 3'd3) phase <= VERIFY;
                        else begin step <= step + 1'b1; phase <= ISSUE; end
                    end else begin
                        error_seen <= 1'b1;
                        phase <= DONE;
                    end
                end
                VERIFY: begin
                    // Explicit on-chip memory readback; a lit LED alone is not enough.
                    if (rd_exists && rd_state == expected_read &&
                        node_count == 8'd4 && !overflow_seen) begin
                        readback_passed[scan_idx] <= 1'b1;
                        if (scan_idx == 2'd3) phase <= DONE;
                        else scan_idx <= scan_idx + 1'b1;
                    end else begin error_seen <= 1'b1; phase <= DONE; end
                end
                default: phase <= DONE;
            endcase
        end
    end

    wire all_passed = (steps_passed == 4'b1111) &&
                      (readback_passed == 4'b1111);
    wire ok = (phase == DONE) && !error_seen && all_passed &&
              (node_count == 8'd4) && !overflow_seen;

    // Arty A7 discrete LEDs show four test observations; RGB0 indicates result.
    assign led = steps_passed;
    assign rgb0_g = ok;
    assign rgb0_r = (phase == DONE) && !ok;
    assign rgb0_b = (phase != DONE);
endmodule
