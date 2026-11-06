"""Generate an electrically minimal STRMKRD Rev0 I2C/SPI pass-through adapter PCB.

This is an INTERPOSER for separate tested breakout modules and a host adapter,
not the full secure-element/photonic/iSPU production board. Kicad DRC and
fabrication review MUST pass separately; no sensor or secure silicon on board.
"""
from pathlib import Path
import argparse
import uuid

NETS = ["", "+3V3_I2C","GND_I2C","SDA1","SCL1",
        "+3V3_DISPLAY","GND_DISPLAY","SPI_SCLK","SPI_MOSI","SPI_CS",
        "EINK_DC","EINK_RST","EINK_BUSY"]
NETMAP={n:i for i,n in enumerate(NETS)}
I2C_NETS=NETS[1:5]
SPI_NETS=NETS[5:]
CONNECTORS=[
    ("J1", 14,20,I2C_NETS,"HOST_I2C"),
    ("J2", 36,20,I2C_NETS,"MCP9808"),
    ("J3", 57,20,I2C_NETS,"INA226"),
    ("J4", 78,20,I2C_NETS,"P256_SE"),
    ("J5", 14,40,SPI_NETS,"HOST_SPI"),
    ("J6", 78,40,SPI_NETS,"EINK_SPI"),
]

def uid(path:str)->str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS,"strmkrd-rev0-interposer:"+path))

def new_footprint(ref,x,y,nets,label):
    size=len(nets)
    span=(size-1)*2.54
    footprint_name=f"STRMKRD_Connector:PinHeader_1x{size:02d}_P2.54mm"
    content=[
        f'  (footprint "{footprint_name}" (layer "F.Cu") (tstamp "{uid(ref)}")',
        f'    (at {x} {y})',
        '    (attr through_hole)',
        f'    (fp_text reference "{ref}" (at 0 -3.4) (layer "F.SilkS")',
        '      (effects (font (size 1 1) (thickness 0.15))))',
        f'    (fp_text value "{label}" (at 0 {span+3.2:.2f}) (layer "F.Fab")',
        '      (effects (font (size 1 1) (thickness 0.15))))',
        f'    (fp_line (start -1.5 -1.5) (end 1.5 -1.5) (stroke (width 0.12) (type default)) (layer "F.SilkS") (tstamp "{uid(ref+"s1")}"))',
        f'    (fp_line (start -1.5 -1.5) (end -1.5 {span+1.5:.2f}) (stroke (width 0.12) (type default)) (layer "F.SilkS") (tstamp "{uid(ref+"s2")}"))',
        f'    (fp_line (start -1.5 {span+1.5:.2f}) (end 1.5 {span+1.5:.2f}) (stroke (width 0.12) (type default)) (layer "F.SilkS") (tstamp "{uid(ref+"s3")}"))',
        f'    (fp_line (start 1.5 -1.5) (end 1.5 {span+1.5:.2f}) (stroke (width 0.12) (type default)) (layer "F.SilkS") (tstamp "{uid(ref+"s4")}"))',
        f'    (fp_rect (start -1.75 -1.75) (end 1.75 {span+1.75:.2f})',
        f'      (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd") (tstamp "{uid(ref+"court")}"))',
    ]
    for pin,net in enumerate(nets,1):
        local_y=(pin-1)*2.54
        pinshape="rect" if pin==1 else "oval"
        content.append(
            f'    (pad "{pin}" thru_hole {pinshape} (at 0 {local_y:.2f}) '
            f'(size 1.7 1.7) (drill 1.0) (layers "*.Cu" "*.Mask") '
            f'(net {NETMAP[net]} "{net}") (tstamp "{uid(ref+str(pin))}"))'
        )
    content.append("  )")
    return "\n".join(content)

def segment(net,x1,y1,x2,y2,width=0.38):
    return (
        f'  (segment (start {x1:.2f} {y1:.2f}) (end {x2:.2f} {y2:.2f}) '
        f'(width {width:.2f}) (layer "F.Cu") (net {NETMAP[net]}) '
        f'(tstamp "{uid(net+str(x1)+str(y1)+str(x2)+str(y2))}"))'
    )

def edge(x1,y1,x2,y2,tag):
    return (f'  (gr_line (start {x1} {y1}) (end {x2} {y2}) '
            f'(stroke (width 0.1) (type default)) (layer "Edge.Cuts") '
            f'(tstamp "{uid(tag)}"))')

def board_text():
    doc=['(kicad_pcb (version 20221018) (generator "strmkrd_rev0_interposer_generator")',
         '  (general (thickness 1.6))','  (paper "A4")',
         '  (layers',
         '    (0 "F.Cu" signal)',
         '    (31 "B.Cu" signal)',
         '    (36 "B.SilkS" user)',
         '    (37 "F.SilkS" user)',
         '    (38 "B.Mask" user)',
         '    (39 "F.Mask" user)',
         '    (41 "F.CrtYd" user)',
         '    (44 "Edge.Cuts" user)',
         '    (49 "F.Fab" user)',
         '  )',
         '  (setup (pad_to_mask_clearance 0))']
    doc.extend(f'  (net {i} "{n}")' for i,n in enumerate(NETS))
    for ref,x,y,nets,label in CONNECTORS:
        doc.append(new_footprint(ref,x,y,nets,label))
    for net_i,net in enumerate(I2C_NETS):
        row_y=20+net_i*2.54
        for left,right in [(14,36),(36,57),(57,78)]:
            doc.append(segment(net,left,row_y,right,row_y,0.45 if net_i<=1 else 0.38))
    for net_i,net in enumerate(SPI_NETS):
        row_y=40+net_i*2.54
        doc.append(segment(net,14,row_y,78,row_y,0.4 if net_i<=1 else 0.38))
    for args in [(5,8,88,8,"edgetop"),(88,8,88,66,"edgeright"),
                 (88,66,5,66,"edgebottom"),(5,66,5,8,"edgeleft")]:
        doc.append(edge(*args))
    # This board contains no physical secure IC, sensor die or power regulator.
    doc.append(")")
    return "\n".join(doc)+"\n"

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",default="hardware/strmkrd-node/kicad/STRMKRD_REV0_INTERPOSER.kicad_pcb")
    args=parser.parse_args()
    destination=Path(args.out);destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(board_text())
    print("CAD_SEED_WRITTEN",destination,"connectors",len(CONNECTORS),
          "nets",len(NETS)-1,"status","DRC_REQUIRED")
