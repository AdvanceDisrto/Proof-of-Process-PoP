# iProvidence Line (iPL)

This directory contains a C++17 proof-of-process simulation kernel for an iPL transit control architecture.

Scope:
- V2V event capture
- track-switch authorization state
- aerodynamic evaluation
- fail-closed gating
- process receipts for each subsystem

This is a deterministic simulation boundary, not a certified railway signaling or safety system.

Build with MSVC:
cl /EHsc /W4 /std:c++17 ipl_core_v2.cpp /Fe:iPL_System_v2.exe

Build with a portable C++17 compiler:
c++ -std=c++17 -Wall -Wextra -pedantic ipl_core_v2.cpp -o iPL_System_v2

Truth boundary: VERIFIED_PROCESS means the simulator's declared checks passed for that event. QUARANTINED stops the simulation and preserves the failure event for replay/correction.