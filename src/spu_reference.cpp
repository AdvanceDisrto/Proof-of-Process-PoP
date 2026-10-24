#include "spu_reference.hpp"
namespace spu {
static std::uint8_t parity_bits(std::uint64_t x) {
  std::uint8_t p=0; for(int i=0;i<64;i++) p ^= ((x>>i)&1u) << (i%8); return p;
}
EccWord ecc_encode(std::uint64_t data) { return {data, parity_bits(data)}; }
std::optional<std::uint64_t> ecc_decode(EccWord word) {
  return parity_bits(word.data)==word.parity ? std::optional<std::uint64_t>{word.data} : std::nullopt;
}
std::uint32_t vector_add(std::uint32_t a,std::uint32_t b){return a+b;}
bool mmio_region_valid(MmioRegion r){return r.size>0 && r.base<=UINT64_MAX-r.size;}
bool mmio_contains(MmioRegion r,std::uint64_t o,std::uint64_t w){return mmio_region_valid(r)&&o<=r.size&&w<=r.size-o;}
}
