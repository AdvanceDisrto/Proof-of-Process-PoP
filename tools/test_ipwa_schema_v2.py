import json,pathlib
from jsonschema import Draft202012Validator
root=pathlib.Path(".")
for name,receipt in [
("ITM-FED-DISBURSEMENT-v1","FED_DISBURSEMENT_RECEIPT"),
("ITM-GLOBAL-LEDGER-v1","GLOBAL_LEDGER_RECEIPT")]:
 schema=json.loads((root/"schemas"/(name+".schema.json")).read_text())
 Draft202012Validator.check_schema(schema)
 validator=Draft202012Validator(schema)
 draft=json.loads((root/"receipts"/(receipt+".json")).read_text())
 assert validator.is_valid(draft), list(validator.iter_errors(draft))
 draft["state"]="READY_FOR_INDEPENDENT_REVIEW"
 assert not validator.is_valid(draft), "unsigned draft promoted to review"
 draft["state"]="DRAFT_PENDING_ATTESTATION"
 draft["body"]["amount_minor"]=-1
 assert not validator.is_valid(draft), "negative payment amount accepted"
 print(name,"DRAFT_PASS_UNSIGNED_PROMOTION_REJECTED_NEGATIVE_AMOUNT_REJECTED")
