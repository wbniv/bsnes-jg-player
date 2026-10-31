#pragma once
#include <array>
#include <atomic>
#include <algorithm>
#include <cstdint>
#include <cstddef>

// Single producer (emulator thread), single consumer (audio render thread).
// Drop new frames on overflow; silence underruns. No allocations or locks.
class AudioRing {
public:
    static constexpr uint32_t capacity = 8192;
    static_assert(std::atomic<uint32_t>::is_always_lock_free);
    uint32_t push(const float* interleaved, size_t sampleCount) noexcept {
        auto w = write_.load(std::memory_order_relaxed);
        auto r = read_.load(std::memory_order_acquire);
        auto frames = static_cast<uint32_t>(sampleCount / 2);
        auto count = std::min(frames, capacity - (w - r));
        for (uint32_t i = 0; i < count; ++i) {
            auto index = ((w + i) % capacity) * 2;
            data_[index] = interleaved[i * 2];
            data_[index + 1] = interleaved[i * 2 + 1];
        }
        write_.store(w + count, std::memory_order_release);
        dropped.fetch_add(frames - count, std::memory_order_relaxed);
        return count;
    }
    void render(float* left, float* right, uint32_t frames) noexcept {
        auto r = read_.load(std::memory_order_relaxed);
        auto w = write_.load(std::memory_order_acquire);
        auto count = std::min(frames, w - r);
        bool silent = muted.load(std::memory_order_relaxed);
        for (uint32_t i = 0; i < frames; ++i) {
            auto index = ((r + i) % capacity) * 2;
            left[i] = i < count && !silent ? data_[index] : 0;
            right[i] = i < count && !silent ? data_[index + 1] : 0;
        }
        read_.store(r + count, std::memory_order_release);
        rendered.fetch_add(count, std::memory_order_relaxed);
        underrun.fetch_add(frames - count, std::memory_order_relaxed);
    }
    // Only after producer and consumer have stopped.
    void clear() noexcept { read_.store(0); write_.store(0); }
    uint32_t queued() const noexcept {
        auto r = read_.load(std::memory_order_acquire);
        return std::min(capacity, write_.load(std::memory_order_acquire) - r);
    }
    std::atomic<bool> muted{false};
    std::atomic<uint32_t> dropped{0}, underrun{0}, rendered{0};
private:
    std::array<float, capacity * 2> data_{};
    std::atomic<uint32_t> read_{0}, write_{0};
};
