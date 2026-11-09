"""Optional real libz3 proof about a NARROW WORKFLOW policy, not about law.

The expression is deliberately transparent, boolean and bounded. Z3 is not
used to certify documents, courts, patient facts, or model outputs.
"""
from __future__ import annotations
import ctypes as C, ctypes.util

class SolverUnavailable(RuntimeError): pass

class NativeZ3:
    def __init__(self):
        path=ctypes.util.find_library('z3')
        if not path:raise SolverUnavailable('native libz3 unavailable')
        self.lib=C.CDLL(path)
        functions=[('Z3_mk_config',C.c_void_p,[]),('Z3_del_config',None,[C.c_void_p]),
                   ('Z3_mk_context',C.c_void_p,[C.c_void_p]),('Z3_del_context',None,[C.c_void_p]),
                   ('Z3_mk_solver',C.c_void_p,[C.c_void_p]),
                   ('Z3_solver_inc_ref',None,[C.c_void_p,C.c_void_p]),
                   ('Z3_solver_dec_ref',None,[C.c_void_p,C.c_void_p]),
                   ('Z3_solver_from_string',None,[C.c_void_p,C.c_void_p,C.c_char_p]),
                   ('Z3_solver_check',C.c_int,[C.c_void_p,C.c_void_p]),
                   ('Z3_mk_params',C.c_void_p,[C.c_void_p]),
                   ('Z3_params_inc_ref',None,[C.c_void_p,C.c_void_p]),
                   ('Z3_params_dec_ref',None,[C.c_void_p,C.c_void_p]),
                   ('Z3_mk_string_symbol',C.c_void_p,[C.c_void_p,C.c_char_p]),
                   ('Z3_params_set_uint',None,[C.c_void_p,C.c_void_p,C.c_void_p,C.c_uint]),
                   ('Z3_solver_set_params',None,[C.c_void_p,C.c_void_p,C.c_void_p])]
        for name,ret,args in functions:
            fn=getattr(self.lib,name)
            fn.restype=ret;fn.argtypes=args

    def check(self, script:str,timeout_ms:int=1000)->str:
        lib=self.lib
        cfg=lib.Z3_mk_config();ctx=lib.Z3_mk_context(cfg);lib.Z3_del_config(cfg)
        if not ctx:raise SolverUnavailable('context init failed')
        solver=lib.Z3_mk_solver(ctx);lib.Z3_solver_inc_ref(ctx,solver)
        params=lib.Z3_mk_params(ctx);lib.Z3_params_inc_ref(ctx,params)
        try:
            lib.Z3_params_set_uint(ctx,params,lib.Z3_mk_string_symbol(ctx,b'timeout'),timeout_ms)
            lib.Z3_solver_set_params(ctx,solver,params)
            lib.Z3_solver_from_string(ctx,solver,script.encode('ascii'))
            return {1:'sat',-1:'unsat',0:'unknown'}.get(lib.Z3_solver_check(ctx,solver),'unknown')
        finally:
            lib.Z3_params_dec_ref(ctx,params)
            lib.Z3_solver_dec_ref(ctx,solver)
            lib.Z3_del_context(ctx)


def check_workflow_constraints(all_defined:bool, all_evidence:bool, notice:bool,
                               reply:bool, counsel:bool)->dict:
    """Ask Z3 if RELEASE can coexist with current workflow premises.

    Even SAT only means consistent workflow flags, NOT that legal elements hold.
    """
    vals=[all_defined,all_evidence,notice,reply,counsel]
    if any(type(x) is not bool for x in vals):raise ValueError('boolean inputs only')
    keys=['all_defined','all_evidence','notice','reply','counsel']
    code='(set-logic QF_UF)\n'
    code+=''.join(f'(declare-const {k} Bool)\n(assert (= {k} {str(x).lower()}))\n' for k,x in zip(keys,vals))
    code+='(declare-const can_release Bool)\n'
    code+='(assert (= can_release (and all_defined all_evidence notice reply counsel)))\n'
    code+='(assert can_release)\n'
    try:
        result=NativeZ3().check(code)
    except (SolverUnavailable,OSError) as exc:
        return {'solver':'native-libz3','status':'UNKNOWN','release_gate':'BLOCKED','reason':str(exc),
                'does_not_prove':'legal truth or physical measurement'}
    return {'solver':'native-libz3','status':result.upper(),
            'release_gate':'DRAFT_FOR_COUNSEL_ONLY' if result=='sat' else 'BLOCKED',
            'does_not_prove':'legal truth or physical measurement'}
