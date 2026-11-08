// SPDX-License-Identifier: Apache-2.0
// PoPC-PU v0.1 OPERATOR-SUPPLIED-PREDICATE request gate, not a PUF/ADC/SAT/crypto core.
// Single-cycle sign_request pulse only when eight externally supplied flags are all asserted.
// A malicious host can spoof flags: this is NOT a physical-attestation boundary.
module popc_gate (
    input wire clk,
    input wire reset_n,
    input wire cmd_valid,
    input wire math_verified,
    input wire meter_fresh,
    input wire meter_calibrated,
    input wire energy_in_range,
    input wire thermal_ok,
    input wire signer_ready,
    input wire consent,
    input wire source_attested,
    input wire [255:0] claim_sha256,
    output reg processed,
    output reg sign_request,
    output reg reject,
    output reg [7:0] fail_mask,
    output reg [255:0] permitted_claim_sha256
);
    wire [7:0] flags = {
       math_verified, meter_fresh, meter_calibrated, energy_in_range,
       thermal_ok, signer_ready, consent, source_attested
    };
    always @(posedge clk or negedge reset_n) begin
       if (!reset_n) begin
          processed <= 1'b0;
          sign_request <= 1'b0;
          reject <= 1'b0;
          fail_mask <= 8'hff;
          permitted_claim_sha256 <= 256'b0;
       end else begin
          processed <= 1'b0;
          sign_request <= 1'b0;
          reject <= 1'b0;
          if (cmd_valid) begin
             processed <= 1'b1;
             fail_mask <= ~flags;
             // Nonzero digest guard is only a sentinel check, NOT SHA verification.
             if (&flags && |claim_sha256) begin
                sign_request <= 1'b1;
                permitted_claim_sha256 <= claim_sha256;
             end else begin
                reject <= 1'b1;
                permitted_claim_sha256 <= 256'b0;
             end
          end
       end
    end
endmodule
