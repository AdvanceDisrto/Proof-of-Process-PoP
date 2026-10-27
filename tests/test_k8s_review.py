from pathlib import Path
import yaml
D=Path('infra/k8s/REVIEW_ONLY.yaml')
H=Path('infra/k8s/TPM_BAREMETAL_REFERENCE.yaml')
def docs(p):return list(yaml.safe_load_all(p.read_text()))

def test_three_jurors_are_independent_deployments_and_hardened():
    k=docs(D)
    jurors=[x for x in k if x.get('kind')=='Deployment' and x['metadata']['name'].startswith('juror-')]
    assert set(x['metadata']['name'] for x in jurors)=={'juror-a','juror-b','juror-c'}
    for x in jurors:
        spec=x['spec']['template']['spec']
        assert len(spec['containers'])==1
        assert spec['automountServiceAccountToken'] is False
        assert 'podAntiAffinity' in spec['affinity']
        assert spec['containers'][0]['securityContext']['allowPrivilegeEscalation'] is False
        assert spec['containers'][0]['securityContext']['capabilities']['drop']==['ALL']

def test_distinct_verifier_namespace_and_relay_only_policy():
    k=docs(D)
    relay=next(x for x in k if x.get('kind')=='Deployment' and x['metadata']['name']=='attest-relay')
    verifier=next(x for x in k if x.get('kind')=='Deployment' and x['metadata']['name']=='receipt-verifier')
    assert relay['metadata']['namespace']=='innovulis-core'
    assert verifier['metadata']['namespace']=='innovulis-verify'
    np=next(x for x in k if x.get('kind')=='NetworkPolicy' and x['metadata']['name']=='verifier-allow-relay-only')
    assert np['spec']['ingress'][0]['from'][0]['podSelector']['matchLabels']=={'app':'attest-relay'}
    assert np['spec']['egress']==[]
    assert np['spec']['ingress'][0]['from'][0]['namespaceSelector']['matchLabels']=={'kubernetes.io/metadata.name':'innovulis-core'}

def test_all_workload_images_intentionally_unpublished_and_unprivileged():
    for x in docs(D)+docs(H):
        if x['kind'] not in ('Deployment','StatefulSet'):continue
        p=x['spec']['template']['spec']
        for c in p['containers']:
            assert c['image'].startswith('registry.invalid/')
            assert c['securityContext'].get('privileged',False) is False
            assert c['securityContext']['runAsNonRoot']
            assert c['securityContext']['capabilities']['drop']==['ALL']
            assert 'SYS_RAWIO' not in c['securityContext']['capabilities'].get('add',[])

def test_baremetal_tpm_set_requires_five_distinct_hosts_no_puf_claim():
    x=docs(H)[0]
    assert x['spec']['replicas']==5
    p=x['spec']['template']['spec']
    assert p['nodeSelector']['innovulis.io/operator-verified-baremetal-tpm2']=='true'
    assert p['affinity']['podAntiAffinity']['requiredDuringSchedulingIgnoredDuringExecution'][0]['topologyKey']=='kubernetes.io/hostname'
    assert p['containers'][0]['resources']['limits']['innovulis.io/tpm2']=='1'

