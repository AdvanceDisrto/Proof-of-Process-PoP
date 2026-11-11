// SPDX-License-Identifier: Apache-2.0
// Tessera-G v0.1: synthesizable single-tile DAG STATUS propagator.
// This block does NOT perform Z3, SHA-256, signature verification, or sensor authentication.
// A trusted external verifier must supply cmd_verdict for a declared formal statement.
// Nodes are append-only, and every parent must refer to a strictly earlier node.
// Time complexity: O(V+E) sequential ingestion, O(1) comparisons per node (max 2 parents).
module tessera_g_dag_tile #(
    parameter integer MAX_NODES = 16,
    parameter integer IDX_W = 8
) (
    input  wire                 clk,
    input  wire                 reset_n,
    input  wire                 cmd_valid,
    output wire                 cmd_ready,
    input  wire [1:0]           cmd_verdict,  // 1=proved by external checker, 2=refuted, 3=unknown
    input  wire [IDX_W-1:0]     cmd_parent_a, // all ones => no parent
    input  wire [IDX_W-1:0]     cmd_parent_b,
    output reg                  cmd_accepted,
    output reg  [2:0]           cmd_state,
    output reg  [IDX_W-1:0]     cmd_index,
    output reg  [IDX_W-1:0]     node_count,
    output reg                  overflow_seen,
    input  wire                 rd_valid,
    input  wire [IDX_W-1:0]     rd_index,
    output reg                  rd_exists,
    output reg  [2:0]           rd_state
);
    localparam integer ADDR_W = (MAX_NODES > 1) ? $clog2(MAX_NODES) : 1;
    localparam [IDX_W-1:0] MAX_NODES_COUNT = IDX_W'(MAX_NODES);
    localparam [IDX_W-1:0] NO_PARENT = {IDX_W{1'b1}};
    localparam [2:0] EMPTY = 3'd0;
    localparam [2:0] ACCEPTED = 3'd1;
    localparam [2:0] REFUTED = 3'd2;
    localparam [2:0] DEPENDENCY_BLOCKED = 3'd3;
    localparam [2:0] UNDETERMINED = 3'd4;
    localparam [2:0] INVALID_TOPOLOGY = 3'd5;

    reg [2:0] state_memory [0:MAX_NODES-1];
    reg [2:0] computed_state;
    reg topology_ok;
    reg dependencies_ok;
    // MAX_NODES must be smaller than 2^IDX_W-1, preserving the sentinel value.
    assign cmd_ready = (node_count < MAX_NODES_COUNT);

    always @* begin
        topology_ok = 1'b1;
        dependencies_ok = 1'b1;
        // A node may not depend on itself, a future node, or an out-of-range ID.
        if (cmd_parent_a != NO_PARENT) begin
            if (cmd_parent_a >= node_count) begin
                topology_ok = 1'b0;
            end else if (state_memory[cmd_parent_a[ADDR_W-1:0]] != ACCEPTED) begin
                dependencies_ok = 1'b0;
            end
        end
        if (cmd_parent_b != NO_PARENT) begin
            if (cmd_parent_b >= node_count) begin
                topology_ok = 1'b0;
            end else if (state_memory[cmd_parent_b[ADDR_W-1:0]] != ACCEPTED) begin
                dependencies_ok = 1'b0;
            end
        end
        if ((cmd_parent_a != NO_PARENT) &&
            (cmd_parent_a == cmd_parent_b)) begin
            topology_ok = 1'b0;
        end
        computed_state = UNDETERMINED;
        if (!topology_ok) begin
            computed_state = INVALID_TOPOLOGY;
        end else if (!dependencies_ok) begin
            computed_state = DEPENDENCY_BLOCKED;
        end else if (cmd_verdict == 2'd1) begin
            computed_state = ACCEPTED;
        end else if (cmd_verdict == 2'd2) begin
            computed_state = REFUTED;
        end
    end

    always @* begin
        rd_exists = 1'b0;
        rd_state = EMPTY;
        if (rd_valid && (rd_index < node_count)) begin
            rd_exists = 1'b1;
            rd_state = state_memory[rd_index[ADDR_W-1:0]];
        end
    end

    // Reset invalidates all old records by clearing the count.
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            node_count <= {IDX_W{1'b0}};
            cmd_accepted <= 1'b0;
            cmd_state <= EMPTY;
            cmd_index <= {IDX_W{1'b0}};
            overflow_seen <= 1'b0;
        end else begin
            cmd_accepted <= 1'b0;
            if (cmd_valid && cmd_ready) begin
                state_memory[node_count[ADDR_W-1:0]] <= computed_state;
                cmd_state <= computed_state;
                cmd_index <= node_count;
                node_count <= node_count + 1'b1;
                cmd_accepted <= 1'b1;
            end else if (cmd_valid && !cmd_ready) begin
                overflow_seen <= 1'b1;
            end
        end
    end
endmodule
