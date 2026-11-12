"""Repo-native i™ iWay SPU/iSPU adapter -> actual KRDID CIH receipt tests.

No live ARC-AGI-3, real GPU, vendor deployment, true legal consent or EPU meter.
"""
import copy
import pytest
from cih_api.test_app import client, secure_config, authorize
from iway.unified_contract import (
    PROFILE_NAMES, digest, policy_hash, linux_inventory,
    local_work, to_existing_cih_request, static_arc, identify_os_release
)

TOY={"train":[
    {"input":[[0,1],[1,0]],"output":[[1,0],[0,1]]},
    {"input":[[0,0],[1,1]],"output":[[1,1],[0,0]]}
],"test":[{"input":[[0,1,0],[1,0,1]]}]}


def work(**opts):
    options={"os_release_text":"NAME=Ubuntu\nID=ubuntu",
             "country":"US","context_source":"OPERATOR_TEST_FIXTURE",
             "accepted_policy_sha256":policy_hash("US")}
    options.update(opts)
    return local_work("ARC_GRID",copy.deepcopy(TOY),**options)


def test_exact_24_linux_inventory_not_deployed():
    listing=linux_inventory()
    assert len(PROFILE_NAMES)==listing["count"]==24
    assert listing["deployed"]==listing["runtime_tested"]==0


@pytest.mark.parametrize("name",PROFILE_NAMES)
def test_all_24_profiles_are_labels_only(name):
    r=identify_os_release('NAME="'+name+'"\nID=unknown')
    assert r["declared_profile"]==name
    assert r["hardware_identity"]=="NOT_ATTESTED"


def test_inversion_toy_solved_without_exec_or_llm():
    result=work()
    assert result["status"]=="EXECUTED"
    assert result["result"]["predictions"]==[[[1,0,1],[0,1,0]]]
    assert result["result"]["scored_official_benchmark"] is False
    assert result["arc_agi3"]=="NOT_EXECUTED"


def test_missing_consent_fails_closed():
    assert work(accepted_policy_sha256=None)["status"]=="REFUSED"


def test_untrusted_country_claim_fails_closed():
    r=work(context_source="IP_REQUEST_HEADER")
    assert r["status"]=="REFUSED"


def test_unknown_country_fails_closed():
    r=work(country="ZZ")
    assert r["status"]=="REFUSED"


def test_bad_rule_no_prediction_claim():
    task={"train":[{"input":[[1]],"output":[[9]]}],
          "test":[{"input":[[0]]}]}
    assert static_arc(task)["status"]=="REFUSED"


def test_provenance_does_not_claim_truth():
    r=work()
    assert "source truth" in r["does_not_prove"]
    assert r["node"]["hardware_identity"]=="NOT_ATTESTED"


def test_unmeasured_joules_are_null():
    r=work()
    assert r["measurement"]["energy_joules"]=={"status":"NOT_MEASURED","value":None}
    assert r["measurement"]["cpu_cycles"]["value"] is None


def test_geometry_separate_from_agi():
    from iway.unified_contract import local_work
    r=local_work("ARC_LENGTH",{"radius":6,"angle":90,"unit":"degrees"},
                 os_release_text="NAME=Debian\nID=debian",
                 country="US",context_source="OPERATOR_TEST_FIXTURE",
                 accepted_policy_sha256=policy_hash("US"))
    assert r["status"]=="EXECUTED"
    assert abs(r["result"]["arc_length"]-9.42477796076938)<1e-12


def test_existing_cih_issues_and_verifies_signed_iway_receipt(secure_config):
    payload=to_existing_cih_request(work())
    r=client.post("/api/v1/receipts",json=payload,
                  headers=authorize(secure_config,payload))
    assert r.status_code==200,r.text
    receipt=r.json()
    assert receipt["storage_status"]=="LOCAL_SQLITE_COMMITTED"
    assert receipt["body"]["evidence_sha256"]==payload["expected_evidence_sha256"]
    assert client.post("/api/v1/verify",json=receipt).json()["integrity_valid"] is True


def test_existing_cih_requires_signer_for_iway(secure_config):
    payload=to_existing_cih_request(work())
    response=client.post("/api/v1/receipts",json=payload)
    assert response.status_code==401
    assert response.json()["detail"]=="KRDID_SIGNATURE_REQUIRED"


def test_existing_cih_replay_rejected(secure_config):
    payload=to_existing_cih_request(work())
    headers=authorize(secure_config,payload)
    assert client.post("/api/v1/receipts",json=payload,headers=headers).status_code==200
    replay=client.post("/api/v1/receipts",json=payload,headers=headers)
    assert replay.status_code==409


def test_existing_cih_detects_tampered_work_after_auth(secure_config):
    payload=to_existing_cih_request(work())
    headers=authorize(secure_config,payload)
    payload["evidence"]["measurement"]["energy_joules"]={"status":"METERED","value":100}
    response=client.post("/api/v1/receipts",json=payload,headers=headers)
    assert response.status_code in (403,422)


def test_iway_refusal_is_documented_not_an_execution(secure_config):
    payload=to_existing_cih_request(work(accepted_policy_sha256=None))
    assert payload["evidence"]["status"]=="REFUSED"
    result=client.post("/api/v1/receipts",json=payload,
                       headers=authorize(secure_config,payload))
    assert result.status_code==200
    assert result.json()["body"]["assessment"]=="INPUT_DIGEST_MATCHED"
