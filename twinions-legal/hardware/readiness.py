"""Fail-closed iStick feasibility audit. Zero flashing, no chip locking."""
from __future__ import annotations
import json
from pathlib import Path


def check(path):
    m=json.loads(Path(path).read_text())
    requirements=['mcu_or_i2c_host','usb_impedance_stackup_from_fabricator',
                  'schematic_netlist','board_routed_pcb','gerbers_excellon','pick_place',
                  'atecc_key_slot_provisioning_plan']
    missing=[x for x in requirements if not m.get(x)]
    issues=[]
    if 'CH340E' in m.get('components',{}) and not m.get('mcu_or_i2c_host'):
        issues.append('CH340E_IS_USB_UART_ONLY_NOT_AN_EXECUTING_MCU')
    if 'MCP9808' in m.get('components',{}):
        issues.append('MCP9808_TEMPERATURE_IS_NOT_JOULES')
    issues.append('COPPER_PLANES_DO_NOT_PROVE_DPA_IMMUNITY')
    return {'project':'iNNOVULIS iStick','acceptance':'BLOCKED_NO_FABRICABLE_PCB',
            'missing_prerequisites':missing,'engineering_issues':issues,
            'gerber_exported':False,'flash_executed':False,'atecc_locked':False}

if __name__=='__main__':
    import sys
    print(json.dumps(check(sys.argv[1] if len(sys.argv)>1 else Path(__file__).with_name('board_readiness.json')),indent=2))
