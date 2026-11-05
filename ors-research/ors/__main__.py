"""Generate a reproducible, honestly scoped ORS software simulation record."""
import json,platform,sys
from pathlib import Path
from .physics import RingScenario,bootstrap_model,exact_potential_lift_energy_j,impact_energy_j,ideal_delta_kinetic_energy_j,ideal_average_power_w
from .debris import generate_synthetic_cloud,screen_synthetic_cloud
from .receipts import mint_observation,verify,canonical,sha

def main():
    out=Path(sys.argv[1] if len(sys.argv)>1 else 'evidence')
    out.mkdir(parents=True,exist_ok=True)
    ring=RingScenario()
    cloud_p,cloud_v=generate_synthetic_cloud(5000,seed=2026)
    alerts=screen_synthetic_cloud(cloud_p,cloud_v)
    mass=1_000_000
    exact=exact_potential_lift_energy_j(mass)
    naive=mass*9.81*500000
    summary={'schema':'ors/software-model-report/0.1','software_only':True,
      'scenario':ring.to_dict(),'seed_logistics':bootstrap_model(),
      'lift_energy':{'mass_kg':mass,'approx_mgh_j':naive,'exact_spherical_potential_j':exact,
                     'exact_mwh':exact/3.6e9,'naive_mwh':naive/3.6e9,
                     'energy_recapture_can_exceed_input':False},
      'ideal_launch_energy_reference':{'payload_kg':1000,'initial_speed_m_s':0,'final_speed_m_s':11200,
          'kinetic_delta_j':ideal_delta_kinetic_energy_j(1000,0,11200),
          'average_power_w_at_100s_and_100pct':ideal_average_power_w(ideal_delta_kinetic_energy_j(1000,0,11200),100),
          'feasibility':'NOT_ESTABLISHED','flight_dynamics':'NOT_MODELLED',
          'does_not_prove':['flight vehicle could survive','safe propulsion or launch track','actual delta-v available']},
      'governance':{'proposal_status':'DISCUSSION_ONLY',
          'issues':['Outer Space Treaty interpretation and liability','UN COPUOS coordination and debris mitigation obligations',
                    'maritime jurisdiction and environmental assessment','equatorial land/water and indigenous rights',
                    'international licensing, risk pooling and emergency governance'],
          'treaty_status':'NOT_NEGOTIATED'},
      'debris_impact_example':{'mass_kg':10.,'closing_speed_m_s':7600.,'kinetic_j':impact_energy_j(10.,7600.),
        'sensor_data':'NONE','avoidance_control':'NOT_MODELLED'},
      'synthetic_debris':{'count':len(cloud_p),'random_seed':2026,'screening_hits':len(alerts),'top_3':alerts[:3],
         'physics':'constant velocity / discrete geometric screening only'},
      'orbital_attestation':{'trust_basis':'LOCAL_SOFTWARE_ED25519_ONLY','clock':'LOCAL_WALL_CLOCK_UNTRUSTED',
          'orbital_position':'ASSUMED_NOT_MEASURED','bitcoin_ots':'NOT_PERFORMED'},
      'engineering_gates':{'structural_fea':'NOT_IMPLEMENTED','thermal':'NOT_IMPLEMENTED',
          'power_losses':'NOT_MEASURED','launch_cost':'ILLUSTRATIVE','material_containment':'NOT_VERIFIED',
          'sensor_calibration':'NOT_VERIFIED','legal_treaty':'NOT_ESTABLISHED','physical_gate':'ACTION_REQUIRED'},
      'environment':{'python':platform.python_version()},
      'does_not_prove':['construction feasibility','safe impact avoidance','reliable power balance',
                        'real debris track','orbital trusted timestamp','hardware prototype']}
    receipt=mint_observation({'summary_sha256':sha(canonical(summary)),'observation_type':'SYNTHETIC_ORS_MODEL'})
    assert verify(receipt,receipt['public_key_hex'])['ok']
    (out/'ors_simulation_report.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    (out/'ors_local_signed_simulation_receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'scenario':summary['scenario'],'lift_energy':summary['lift_energy'],
        'bootstrap':summary['seed_logistics'],'synthetic_hits':len(alerts),
        'signature_check':'PASS_SELF_DECLARED_KEY','physical_gate':'ACTION_REQUIRED'},indent=2))
if __name__=='__main__':main()
