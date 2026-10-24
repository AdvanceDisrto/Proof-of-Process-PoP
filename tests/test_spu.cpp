#include "spu_reference.hpp"
#include <cassert>
#include <string>
int main(int argc,char**argv){
 std::string t=argc>1?argv[1]:"all";
 if(t=="vector"||t=="all") assert(spu::vector_add(0x12345678u,2u)==0x1234567au);
 if(t=="ecc"||t=="all"){
  auto e=spu::ecc_encode(0x1122334455667788ULL); assert(spu::ecc_decode(e).value()==0x1122334455667788ULL);
  e.data^=1ULL; assert(spu::ecc_decode(e).value()==0x1122334455667788ULL);
  e=spu::ecc_encode(0x1122334455667788ULL); e.data^=3ULL; assert(!spu::ecc_decode(e).has_value());
 }
 if(t=="mmio"||t=="all"){spu::MmioRegion r{0x1000,0x1000}; assert(spu::mmio_region_valid(r)); assert(spu::mmio_contains(r,0x20,8)); assert(!spu::mmio_contains(r,0x1000,1)); assert(!spu::mmio_region_valid({0xfffffffffffffff0ULL,32}));}
 return 0;
}
