#include "spu_reference.hpp"
namespace spu {
static int is_parity_pos(int p){return p==1||p==2||p==4||p==8||p==16||p==32||p==64;}
static bool getbit(const EccWord& w,int pos){
 if(pos>=1&&pos<=71){
  if(is_parity_pos(pos)) int k=0; switch(pos){case 1:k=0;break;case 2:k=1;break;case 4:k=2;break;case 8:k=3;break;case 16:k=4;break;case 32:k=5;break;default:k=6;} return (w.parity>>k)&1u;
  int di=0; for(int p=1;p<pos;p++) if(!is_parity_pos(p)) ++di;
  return (w.data>>di)&1ULL;
 }
 return (w.parity>>7)&1u;
}
static void setbit(EccWord& w,int pos,bool v){
 if(pos>=1&&pos<=71){
  if(is_parity_pos(pos)){int k=0; switch(pos){case 1:k=0;break;case 2:k=1;break;case 4:k=2;break;case 8:k=3;break;case 16:k=4;break;case 32:k=5;break;default:k=6;} if(v) w.parity|=1u<<k; else w.parity&=~(1u<<k); return;}
  int di=0; for(int p=1;p<pos;p++) if(!is_parity_pos(p)) ++di; if(v) w.data|=1ULL<<di; else w.data&=~(1ULL<<di);
 } else {if(v) w.parity|=0x80; else w.parity&=0x7f;}
}
EccWord ecc_encode(std::uint64_t data){
 EccWord w{data,0};
 for(int k=0;k<7;k++){int p=1<<k; bool parity=false; for(int pos=1;pos<=71;pos++) if((pos&p)&&pos!=p) parity ^= getbit(w,pos); setbit(w,p,parity);}
 bool overall=false; for(int pos=1;pos<=71;pos++) overall^=getbit(w,pos); setbit(w,72,overall); return w;
}
std::optional<std::uint64_t> ecc_decode(EccWord w){
 int syndrome=0;
 for(int k=0;k<7;k++){int p=1<<k; bool parity=false; for(int pos=1;pos<=71;pos++) if(pos&p) parity ^= getbit(w,pos); if(parity) syndrome|=p;}
 bool overall=false; for(int pos=1;pos<=72;pos++) overall^=getbit(w,pos);
 if(overall && syndrome){setbit(w,syndrome,!getbit(w,syndrome));}
 else if(!overall && syndrome){return std::nullopt;}
 else if(overall && !syndrome){setbit(w,72,!getbit(w,72));}
 std::uint64_t data=0; int di=0; for(int pos=1;pos<=71;pos++) if(!is_parity_pos(pos)){if(getbit(w,pos)) data|=1ULL<<di; ++di;} return data;
}
std::uint32_t vector_add(std::uint32_t a,std::uint32_t b){return a+b;}
bool mmio_region_valid(MmioRegion r){return r.size>0 && r.base<=UINT64_MAX-r.size;}
bool mmio_contains(MmioRegion r,std::uint64_t o,std::uint64_t w){return mmio_region_valid(r)&&o<=r.size&&w<=r.size-o;}
}
