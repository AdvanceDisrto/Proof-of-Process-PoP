#ifndef OMNIPRESENT_MESH_H
#define OMNIPRESENT_MESH_H
#include "sha256.h"
typedef enum { MESH_LAYER_EDGE=1, MESH_LAYER_ORBITAL=2, MESH_LAYER_AI=3 } MeshLayer;
typedef struct { MeshLayer layer; double node_count, harvested_w_per_node, idle_w_per_node, workload_w_per_node; } LayerBudget;
typedef struct { double total_harvested_w, total_required_w, coverage_ratio; int self_running, any_layer_needs_grid; } MeshResult;
int mesh_compute(const LayerBudget*, int, MeshResult*);
int mesh_emit_receipt(const MeshResult*, ibare_u8 out_hash[32]);
#endif
