#include "spu_reference.hpp"
namespace spu {
static int parity_index(int pos) {
  switch (pos) {
    case 1: return 0; case 2: return 1; case 4: return 2; case 8: return 3;
    case 16: return 4; case 32: return 5; default: return 6;
  }
}
static bool is_parity_pos(int p) { return p==1||p==2||p==4||p==8||p==16||p==32||p==64; }
static bool getbit(const EccWord& w,int pos) {
  if (pos==72) return (w.parity & 0x80u)!=0;
  if (is_parity_pos(pos)) return ((w.parity >> parity_index(pos)) & 1u)!=0;
  int di=0; for(int p=1;p<pos;p++) if(!is_parity_pos(p)) ++di;
  return ((w.data >> di) & 1ULL)!=0;
}
static void setbit(EccWord& w,int pos,bool v) {
  if (pos==72) { if(v) w.parity|=0x80u; else w.parity&=0x7fu; return; }
  if (is_parity_pos(pos)) { const int k=parity_index(pos); if(v) w.parity|=1u<<k; else w.parity&=static_cast<std::uint8_t>(~(1u<<k)); return; }
  int di=0; for(int p=1;p<pos;p++) if(!is_parity_pos(p)) ++di;
  if(v) w.data|=1ULL<<di; else w.data&=~(1ULL<<di);
}
EccWord ecc_encode(std::uint64_t data) {
  EccWord w{data,0};
  for(int k=0;k<7;k++){ const int p=1<<k; bool x=false; for(int pos=1;pos<=71;pos++) if((pos&p)!=0 && pos!=p) x^=getbit(w,pos); setbit(w,p,x); }
  bool overall=false; for(int pos=1;pos<=71;pos++) overall^=getbit(w,pos); setbit(w,72,overall);
  return w;
}
std::optional<std::uint64_t> ecc_decode(EccWord w) {
  int syndrome=0;
  for(int k=0;k<7;k++){ const int p=1<<k; bool x=false; for(int pos=1;pos<=71;pos++) if((pos&p)!=0) x^=getbit(w,pos); if(x) syndrome|=p; }
  bool overall=false; for(int pos=1;pos<=72;pos++) overall^=getbit(w,pos);
  if(overall && syndrome){ if(syndrome<=71) setbit(w,syndrome,!getbit(w,syndrome)); else return std::nullopt; }
  else if(!overall && syndrome) return std::nullopt;
  else if(overall) setbit(w,72,!getbit(w,72));
  std::uint64_t data=0; int di=0; for(int pos=1;pos<=71;pos++) if(!is_parity_pos(pos)){ if(getbit(w,pos)) data|=1ULL<<di; ++di; }
  return data;
}
std::uint32_t vector_add(std::uint32_t a,std::uint32_t b){return a+b;}
bool mmio_region_valid(MmioRegion r){return r.size>0 && r.base<=UINT64_MAX-r.size;}
bool mmio_contains(MmioRegion r,std::uint64_t o,std::uint64_t w){return mmio_region_valid(r)&&o<=r.size&&w<=r.size-o;}
}
