#pragma once
#include <cstdint>
#include <optional>
#include <array>
namespace spu {
struct EccWord { std::uint64_t data{}; std::uint8_t parity{}; };
EccWord ecc_encode(std::uint64_t data);
std::optional<std::uint64_t> ecc_decode(EccWord word);
std::uint32_t vector_add(std::uint32_t a, std::uint32_t b);
struct MmioRegion { std::uint64_t base; std::uint64_t size; };
bool mmio_region_valid(MmioRegion r);
bool mmio_contains(MmioRegion r, std::uint64_t offset, std::uint64_t width);
}
