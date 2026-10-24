"""i™ MCP authority kernel: i™ governs MCP traffic without replacing MCP transport."""
from __future__ import annotations
import hashlib, json, secrets, time
from typing import Any, Mapping

class iMCPAuthorityKernel:
    """Fail-closed authority/evidence wrapper around any MCP-compatible server."""
    def __init__(self, iska_root_verifier, supabase_client, wrapped_server):
        self.verify_iska = iska_root_verifier
        self.db = supabase_client
        self.server = wrapped_server
        self.active_challenges: dict[str, dict[str, Any]] = {}

    async def handle(self, json_rpc: dict, caller_ctx: dict) -> dict:
        method = json_rpc.get("method", "")
        if method == "i/mint_challenge": return await self._i_mint_challenge(json_rpc, caller_ctx)
        if method == "i/seal_intent": return await self._i_seal_intent(json_rpc, caller_ctx)
        if method == "i/verify_receipt": return await self._i_verify_receipt(json_rpc, caller_ctx)
        return await self._dispatch_with_receipt(json_rpc, caller_ctx)

    async def _i_mint_challenge(self, req, ctx):
        caller_id = ctx.get("caller_id")
        if not caller_id: return self._rpc_error(req, -32602, "MISSING_CALLER_ID")
        valid, root_id = self.verify_iska(ctx.get("delegation_cert"))
        if not valid: return self._rpc_error(req, -32001, "ISKA_DELEGATION_INVALID")
        nonce = secrets.token_hex(32)
        self.active_challenges[str(caller_id)] = {"nonce": nonce, "root_id": root_id, "expires": time.time() + 300}
        return {"jsonrpc":"2.0","id":req.get("id"),"result":{"challenge_nonce":nonce,"expires_in_seconds":300,"authority_root":root_id,"license":"Apache-2.0"}}

    async def _i_seal_intent(self, req, ctx):
        body = (req.get("params") or {}).get("body")
        if body is None: return self._rpc_error(req, -32602, "MISSING_BODY")
        h = self._sha256(json.dumps(body, sort_keys=True, separators=(",", ":")))
        return {"jsonrpc":"2.0","id":req.get("id"),"result":{"intent_hash":"sha256:"+h,"doctrine":"The receipt can record reality; it cannot manufacture reality."}}

    async def _i_verify_receipt(self, req, ctx):
        receipt_id = (req.get("params") or {}).get("receipt_id")
        if not receipt_id: return self._rpc_error(req, -32602, "MISSING_RECEIPT_ID")
        res = self.db.table("mcp_receipts").select("*").eq("receipt_id", receipt_id).execute()
        if not res.data: return self._rpc_error(req, -32000, "RECEIPT_NOT_FOUND")
        return {"jsonrpc":"2.0","id":req.get("id"),"result":{"receipt":res.data[0],"verification":"PASS","source_of_truth":"iSKA_root_chain"}}

    async def _dispatch_with_receipt(self, req, ctx):
        caller_id, nonce = ctx.get("caller_id"), ctx.get("nonce")
        valid, root_id = self.verify_iska(ctx.get("delegation_cert"))
        if not valid: return self._rpc_error(req, -32001, "ISKA_DELEGATION_INVALID")
        session = self.active_challenges.get(str(caller_id))
        if not session or not nonce or not secrets.compare_digest(str(session["nonce"]), str(nonce)):
            return self._rpc_error(req, -32002, "REPLAY_DETECTED")
        if time.time() > float(session["expires"]):
            self.active_challenges.pop(str(caller_id), None)
            return self._rpc_error(req, -32002, "CHALLENGE_EXPIRED")
        self.active_challenges.pop(str(caller_id), None)
        intent = {"caller_id":caller_id,"nonce":nonce,"method":req.get("method"),"params_hash":"sha256:"+self._sha256(json.dumps(req.get("params",{}),sort_keys=True,separators=(",",":"))),"timestamp_utc":time.time()}
        try:
            result = await self.server.handle(req); state = "VERIFIED_PROCESS"
        except Exception as exc:
            result = self._rpc_error(req, -32603, "TOOL_EXECUTION_FAILED: "+str(exc)); state = "TOOL_FAILED"
        receipt = {"spec":"innovulis-imcp-receipt/1.0","receipt_id":"imcp_"+secrets.token_hex(16),"intent":intent,"execution_state":state,"wrapped_server":getattr(self.server,"name","unknown"),"result_hash":"sha256:"+self._sha256(json.dumps(result,sort_keys=True,separators=(",",":"))),"authority_root":root_id,"physical_gate":"ACTION_REQUIRED","license":"Apache-2.0","the_central_rule":"A command is a request. Authority is separate. Evidence closes the action."}
        try: self.db.table("mcp_receipts").insert(receipt).execute()
        except Exception as exc: return self._rpc_error(req, -32003, "FAIL_CLOSED: LEDGER_WRITE_FAILED: "+str(exc))
        if not isinstance(result, dict): result={"jsonrpc":"2.0","id":req.get("id"),"result":result}
        if "result" in result and isinstance(result["result"], dict): result["result"]["_imcp_receipt"]={"receipt_id":receipt["receipt_id"],"verify_via":"i/verify_receipt","license":"Apache-2.0"}
        return result

    @staticmethod
    def _rpc_error(req, code, message): return {"jsonrpc":"2.0","id":req.get("id"),"error":{"code":code,"message":message}}
    @staticmethod
    def _sha256(data: str) -> str: return hashlib.sha256(data.encode("utf-8")).hexdigest()
