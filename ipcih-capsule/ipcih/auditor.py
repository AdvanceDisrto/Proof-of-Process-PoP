"""Buddy audit adapter: actual integer proposition checks only.

Never upgrades a source-backed/medical/model claim merely due to formal consistency.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class AuditResult:
    status:str
    reason:str
    does_not_prove:list[str]

def audit_assertion(claim,*,reference=None):
    limitations=['physical ground truth','medical diagnosis','natural language factual correctness','hardware sensor trust']
    if not isinstance(claim,dict) or claim.get('kind')!='declared_integer_relation':
        return AuditResult('UNRESOLVED','Untranslated or unsupported natural-language claim',limitations)
    if set(claim)!={'kind','lhs','op','rhs'} or type(claim['lhs']) is not int or type(claim['rhs']) is not int or claim['op'] not in ('==','<=','>=','<','>','!='):
        return AuditResult('UNRESOLVED','Untrusted/ambiguous integer statement',limitations)
    a,b=claim['lhs'],claim['rhs']
    if abs(a)>10**12 or abs(b)>10**12:return AuditResult('UNRESOLVED','Out of bounded domain',limitations)
    result={'==':lambda:a==b,'<=':lambda:a<=b,'>=':lambda:a>=b,'<':lambda:a<b,'>':lambda:a>b,'!=':lambda:a!=b}[claim['op']]()
    return AuditResult('DECLARED_ARITHMETIC_TRUE' if result else 'DECLARED_ARITHMETIC_FALSE', 'Evaluated submitted integers; inputs are not independently attested',limitations)
