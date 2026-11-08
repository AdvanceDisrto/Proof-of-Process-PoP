"""Real native libz3 checking of a fixed and pinned QF_LIA demonstration limit.
No natural-language reasoning, external authorization, hardware, or sensor proof.
"""
from __future__ import annotations
import ctypes as C
import ctypes.util

class Z3Unavailable(RuntimeError):
    pass

class Policy:
    def __init__(self):
        path=ctypes.util.find_library("z3")
        if not path:
            raise Z3Unavailable("libz3 unavailable: fail closed")
        self.z=C.CDLL(path)
        for n, r, a in (
            ("Z3_mk_config",C.c_void_p,[]),("Z3_del_config",None,[C.c_void_p]),
            ("Z3_mk_context",C.c_void_p,[C.c_void_p]),
            ("Z3_del_context",None,[C.c_void_p]),
            ("Z3_mk_solver",C.c_void_p,[C.c_void_p]),
            ("Z3_solver_inc_ref",None,[C.c_void_p,C.c_void_p]),
            ("Z3_solver_dec_ref",None,[C.c_void_p,C.c_void_p]),
            ("Z3_solver_from_string",None,[C.c_void_p,C.c_void_p,C.c_char_p]),
            ("Z3_solver_check",C.c_int,[C.c_void_p,C.c_void_p]),
            ("Z3_mk_params",C.c_void_p,[C.c_void_p]),
            ("Z3_params_inc_ref",None,[C.c_void_p,C.c_void_p]),
            ("Z3_params_dec_ref",None,[C.c_void_p,C.c_void_p]),
            ("Z3_mk_string_symbol",C.c_void_p,[C.c_void_p,C.c_char_p]),
            ("Z3_params_set_uint",None,[C.c_void_p,C.c_void_p,C.c_void_p,C.c_uint]),
            ("Z3_solver_set_params",None,[C.c_void_p,C.c_void_p,C.c_void_p]),
        ):
            fn=getattr(self.z,n);fn.restype=r;fn.argtypes=a

    def check(self, script, timeout_ms=1000):
        z=self.z;cfg=z.Z3_mk_config();ctx=z.Z3_mk_context(cfg);z.Z3_del_config(cfg)
        if not ctx: raise Z3Unavailable("no context")
        solver=z.Z3_mk_solver(ctx);z.Z3_solver_inc_ref(ctx,solver)
        params=z.Z3_mk_params(ctx);z.Z3_params_inc_ref(ctx,params)
        try:
            sym=z.Z3_mk_string_symbol(ctx,b"timeout")
            z.Z3_params_set_uint(ctx,params,sym,timeout_ms)
            z.Z3_solver_set_params(ctx,solver,params)
            z.Z3_solver_from_string(ctx,solver,script.encode("ascii"))
            return {-1:"unsat",1:"sat",0:"unknown"}.get(z.Z3_solver_check(ctx,solver),"unknown")
        finally:
            z.Z3_params_dec_ref(ctx,params)
            z.Z3_solver_dec_ref(ctx,solver)
            z.Z3_del_context(ctx)

    def allowed(self, amount, limit):
        if (type(amount) is not int or type(limit) is not int or
            not 0 <= amount <= 10**9 or not 0 <= limit <= 10**9):return False
        axioms=f"(set-logic QF_LIA)\n(declare-const amount Int)\n(assert (= amount {amount}))"
        try:
            return (self.check(axioms)=="sat" and
                    self.check(axioms+f"\n(assert (> amount {limit}))")=="unsat")
        except Z3Unavailable:
            return False
