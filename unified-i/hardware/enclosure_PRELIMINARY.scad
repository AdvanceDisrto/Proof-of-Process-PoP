// iNNOVULIS iStick CONCEPT enclosure for 18 x 45 mm PCB; NOT a fit check.
// No validated shell, ESD qualification, shock certification, or USB fit.
$fn=48;
board_w=18;
board_l=45;
board_h=1.6;
clearance=0.5;
wall=1.8;
inner_w=board_w + 2*clearance;
inner_l=board_l + 2*clearance;
outer_w=inner_w + wall*2;
outer_l=inner_l + wall*2;
outer_h=9;

// One prototype base, not a sealed assembled enclosure.
difference() {
  cube([outer_w,outer_l,outer_h]);
  translate([wall,wall,wall]) cube([inner_w,inner_l,outer_h]);
  // Generic side aperture placeholder. USB-C exact mechanical fit pending.
  translate([outer_w/2-6,-0.3,3]) cube([12,wall+1,5]);
}
