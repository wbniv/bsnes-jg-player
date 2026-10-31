#import "AudioOutput.h"
#import <AVFoundation/AVFoundation.h>
#include "AudioRing.hpp"
#include "CoreHost.hpp"
#include <memory>
#include <cmath>

@implementation BJGAudioOutput {
    AVAudioEngine* _engine;
    AVAudioSourceNode* _source;
    AVAudioPCMBuffer* _offlineBuffer;
    std::shared_ptr<AudioRing> _ring;
    BOOL _offline;
}
- (instancetype)init { return [self initOffline:NO]; }
- (instancetype)initOffline:(BOOL)forceOffline {
    if ((self = [super init])) {
        _offline = forceOffline || [NSProcessInfo.processInfo.environment[@"BJG_AUDIO_OFFLINE"] isEqualToString:@"1"];
        _ring = std::make_shared<AudioRing>();
        auto ring = _ring; // Keeps storage alive even during a trailing audio callback.
        _engine = [AVAudioEngine new];
        AVAudioFormat* format = [[AVAudioFormat alloc] initStandardFormatWithSampleRate:48000 channels:2];
        _source = [[AVAudioSourceNode alloc] initWithFormat:format renderBlock:^OSStatus(BOOL* silence, const AudioTimeStamp* timestamp, AVAudioFrameCount frames, AudioBufferList* buffers) {
            if (buffers->mNumberBuffers != 2) return kAudio_ParamError;
            ring->render(static_cast<float*>(buffers->mBuffers[0].mData),
                         static_cast<float*>(buffers->mBuffers[1].mData), frames);
            *silence = NO;
            return noErr;
        }];
        [_engine attachNode:_source];
        if (_offline) {
            NSError* error = nil;
            if (![_engine enableManualRenderingMode:AVAudioEngineManualRenderingModeOffline format:format maximumFrameCount:1024 error:&error]) {
                NSLog(@"Offline audio configuration failed: %@", error);
                return nil;
            }
            _offlineBuffer = [[AVAudioPCMBuffer alloc] initWithPCMFormat:format frameCapacity:1024];
        }
        // Enter manual mode before touching mainMixerNode: that accessor otherwise
        // initializes RemoteIO, which has no audio device on headless CI runners.
        [_engine connect:_source to:_engine.mainMixerNode format:format];
    }
    return self;
}
- (BOOL)start:(NSError**)error {
    if (_engine.running) return YES;
    if (!_offline) {
        AVAudioSession* session = AVAudioSession.sharedInstance;
        if (![session setCategory:AVAudioSessionCategoryPlayback mode:AVAudioSessionModeDefault options:0 error:error]) return NO;
        if (![session setActive:YES error:error]) return NO;
    }
    [_engine prepare];
    if (![_engine startAndReturnError:error]) return NO;
    PlayerCore::audioSink(_ring.get(), [](void* context, const float* data, size_t samples) {
        static_cast<AudioRing*>(context)->push(data, samples);
    });
    return YES;
}
- (void)stop {
    PlayerCore::audioSink(nullptr, nullptr);
    [_engine stop];
    _ring->clear();
    if (!_offline) [AVAudioSession.sharedInstance setActive:NO withOptions:AVAudioSessionSetActiveOptionNotifyOthersOnDeactivation error:nil];
}
- (void)pumpOffline {
    if (!_offline || !_engine.running) return;
    while (_ring->queued()) {
        auto before = _ring->queued();
        auto count = std::min<uint32_t>(1024, _ring->queued());
        NSError* error = nil;
        if ([_engine renderOffline:count toBuffer:_offlineBuffer error:&error] != AVAudioEngineManualRenderingStatusSuccess) {
            NSLog(@"Offline audio render failed: %@", error);
            break;
        }
        if (_ring->queued() >= before) break;
    }
}
- (void)setMuted:(BOOL)value { _ring->muted.store(value); }
- (BOOL)muted { return _ring->muted.load(); }
- (uint32_t)renderedFrames { return _ring->rendered.load(); }
- (uint32_t)droppedFrames { return _ring->dropped.load(); }
- (uint32_t)underrunFrames { return _ring->underrun.load(); }
- (void)dealloc { [self stop]; [_engine disconnectNodeOutput:_source]; [_engine detachNode:_source]; }
+ (NSDictionary*)verifyOfflineRendering {
    BJGAudioOutput* output = [[BJGAudioOutput alloc] initOffline:YES];
    NSError* error = nil;
    if (!output || ![output start:&error]) return @{@"pass": @NO, @"error": error.localizedDescription ?: @"Audio engine setup failed"};
    float samples[2048];
    for (unsigned i = 0; i < 1024; ++i) {
        float value = 0.25f * std::sin(2.0 * 3.141592653589793 * 440.0 * i / 48000.0);
        samples[i*2] = value; samples[i*2+1] = -value;
    }
    output->_ring->push(samples, 2048);
    auto status = [output->_engine renderOffline:1024 toBuffer:output->_offlineBuffer error:&error];
    double energy = 0, stereoError = 0;
    if (status == AVAudioEngineManualRenderingStatusSuccess) {
        auto channels = output->_offlineBuffer.floatChannelData;
        for (unsigned i = 0; i < output->_offlineBuffer.frameLength; ++i) {
            energy += channels[0][i] * channels[0][i];
            stereoError += std::abs(channels[0][i] + channels[1][i]);
        }
    }
    BOOL pass = status == AVAudioEngineManualRenderingStatusSuccess && energy > 1 && stereoError < 0.01 && output.renderedFrames == 1024;
    [output stop];
    return @{@"pass": @(pass), @"sampleRate": @48000, @"channels": @2, @"frames": @1024,
             @"energy": @(energy), @"stereoError": @(stereoError), @"mode": @"AVAudioEngine offline render (not speaker proof)"};
}
@end
