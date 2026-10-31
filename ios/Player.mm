#import "Player.h"
#import "AudioOutput.h"
#import <MetalKit/MetalKit.h>
#import <GameController/GameController.h>
#import <AVFoundation/AVFoundation.h>
#include "CoreHost.hpp"
#include "DemoConfig.h"
#include "PlayerTiming.hpp"
#include "ControllerInput.hpp"

static bool loadDemo() {
    NSBundle* bundle = NSBundle.mainBundle;
    NSString* rom = [bundle pathForResource:@"demo" ofType:@"sfc"];
    if (!rom) return false;
    return PlayerCore::load(rom.UTF8String, [[bundle.resourcePath stringByAppendingPathComponent:@"Database"] UTF8String]);
}

@interface BJGPlayerController () <MTKViewDelegate>
@end
@implementation BJGPlayerController {
    MTKView* _screen;
    CADisplayLink* _clock;
    id<MTLCommandQueue> _queue;
    id<MTLRenderPipelineState> _pipeline;
    id<MTLTexture> _texture;
    BJGAudioOutput* _audio;
    GCController* _controller;
    NSMutableArray<UIButton*>* _buttons;
    PlayerTiming _timing;
    uint16_t _touchPad, _controllerPad, _lastTouch;
    unsigned _frames, _touchEvents;
    BOOL _ready, _running, _userPaused, _applicationActive, _muted, _interrupted, _closed;
    NSString* _error;
}
- (void)viewDidLoad {
    [super viewDidLoad];
    self.view.backgroundColor = UIColor.blackColor;
    if ([NSProcessInfo.processInfo.arguments containsObject:@"--self-test"]) return;
    id<MTLDevice> device = MTLCreateSystemDefaultDevice();
    _screen = [[MTKView alloc] initWithFrame:CGRectZero device:device];
    _screen.accessibilityIdentifier = @"gameScreen";
    _screen.isAccessibilityElement = YES;
    _screen.accessibilityLabel = @"SNES display";
    _screen.translatesAutoresizingMaskIntoConstraints = NO;
    _screen.paused = YES;
    _screen.enableSetNeedsDisplay = NO;
    _screen.delegate = self;
    _screen.clearColor = MTLClearColorMake(0, 0, 0, 1);
    [self.view addSubview:_screen];
    _queue = [device newCommandQueue];
    NSString* shader = @"#include <metal_stdlib>\nusing namespace metal;\n"
    "struct V { float4 position [[position]]; float2 uv; };\n"
    "vertex V vertexMain(uint i [[vertex_id]]) {\n"
    "float2 p[4]={float2(-1,1),float2(-1,-1),float2(1,1),float2(1,-1)};\n"
    "float2 uv[4]={float2(0,0),float2(0,1),float2(1,0),float2(1,1)};\n"
    "return {float4(p[i],0,1),uv[i]}; }\n"
    "fragment float4 fragmentMain(V v [[stage_in]], texture2d<float> t [[texture(0)]]) {\n"
    "constexpr sampler s(filter::nearest); return float4(t.sample(s,v.uv).rgb,1); }\n";
    NSError* error = nil;
    id<MTLLibrary> library = [device newLibraryWithSource:shader options:nil error:&error];
    MTLRenderPipelineDescriptor* descriptor = [MTLRenderPipelineDescriptor new];
    descriptor.vertexFunction = [library newFunctionWithName:@"vertexMain"];
    descriptor.fragmentFunction = [library newFunctionWithName:@"fragmentMain"];
    descriptor.colorAttachments[0].pixelFormat = _screen.colorPixelFormat;
    if (library) _pipeline = [device newRenderPipelineStateWithDescriptor:descriptor error:&error];

    _buttons = [NSMutableArray new];
    UIStackView* controls = [UIStackView new];
    controls.axis = UILayoutConstraintAxisVertical;
    controls.spacing = 4;
    controls.distribution = UIStackViewDistributionFillEqually;
    controls.translatesAutoresizingMaskIntoConstraints = NO;
    NSArray* labels = @[@"↑", @"↓", @"←", @"→", @"Select", @"Start", @"Y", @"X", @"B", @"A", @"L", @"R"];
    NSArray* names = @[@"Up", @"Down", @"Left", @"Right", @"Select", @"Start", @"Y", @"X", @"B", @"A", @"L", @"R"];
    NSArray* ids = @[@"up", @"down", @"left", @"right", @"select", @"start", @"y", @"x", @"b", @"a", @"l", @"r"];
    const int bits[] = {11, 10, 9, 8, 13, 12, 14, 6, 15, 7, 5, 4};
    for (unsigned row = 0; row < 2; ++row) {
        UIStackView* line = [UIStackView new];
        line.axis = UILayoutConstraintAxisHorizontal;
        line.distribution = UIStackViewDistributionFillEqually;
        line.spacing = 4;
        for (unsigned column = 0; column < 6; ++column) {
            unsigned i = row * 6 + column;
            UIButton* button = [UIButton buttonWithType:UIButtonTypeSystem];
            [button setTitle:labels[i] forState:UIControlStateNormal];
            button.accessibilityLabel = names[i];
            button.accessibilityIdentifier = [@"pad." stringByAppendingString:ids[i]];
            button.backgroundColor = [UIColor colorWithWhite:0.15 alpha:1];
            button.layer.cornerRadius = 8;
            button.tag = 1 << bits[i];
            button.exclusiveTouch = NO;
            [button addTarget:self action:@selector(press:) forControlEvents:UIControlEventTouchDown | UIControlEventTouchDragEnter];
            [button addTarget:self action:@selector(release:) forControlEvents:UIControlEventTouchUpInside | UIControlEventTouchUpOutside | UIControlEventTouchCancel | UIControlEventTouchDragExit];
            [_buttons addObject:button];
            [line addArrangedSubview:button];
        }
        [controls addArrangedSubview:line];
    }
    [self.view addSubview:controls];
    UILayoutGuide* safe = self.view.safeAreaLayoutGuide;
    NSLayoutConstraint* preferredWidth = [_screen.widthAnchor constraintEqualToAnchor:safe.widthAnchor constant:-16];
    preferredWidth.priority = UILayoutPriorityDefaultHigh;
    [NSLayoutConstraint activateConstraints:@[
        [_screen.topAnchor constraintEqualToAnchor:safe.topAnchor constant:4],
        [_screen.centerXAnchor constraintEqualToAnchor:safe.centerXAnchor],
        [_screen.widthAnchor constraintLessThanOrEqualToAnchor:safe.widthAnchor constant:-16],
        [_screen.widthAnchor constraintEqualToAnchor:_screen.heightAnchor multiplier:4.0/3.0],
        preferredWidth,
        [_screen.bottomAnchor constraintLessThanOrEqualToAnchor:controls.topAnchor constant:-8],
        [controls.leadingAnchor constraintEqualToAnchor:safe.leadingAnchor constant:8],
        [controls.trailingAnchor constraintEqualToAnchor:safe.trailingAnchor constant:-8],
        [controls.heightAnchor constraintEqualToConstant:92],
        [controls.bottomAnchor constraintEqualToAnchor:safe.bottomAnchor constant:-4]
    ]];
    _ready = _pipeline && loadDemo();
    if (!_ready) { _error = error.localizedDescription ?: @"Could not load the bundled ROM"; [self emitState]; return; }
    _audio = [BJGAudioOutput new];
    _audio.muted = _muted;
    _clock = [CADisplayLink displayLinkWithTarget:self selector:@selector(tick:)];
    _clock.paused = YES;
    [_clock addToRunLoop:NSRunLoop.mainRunLoop forMode:NSRunLoopCommonModes];
    NSNotificationCenter* center = NSNotificationCenter.defaultCenter;
    [center addObserver:self selector:@selector(controllersChanged:) name:GCControllerDidConnectNotification object:nil];
    [center addObserver:self selector:@selector(controllersChanged:) name:GCControllerDidDisconnectNotification object:nil];
    [center addObserver:self selector:@selector(audioInterruption:) name:AVAudioSessionInterruptionNotification object:nil];
    [center addObserver:self selector:@selector(audioRouteChanged:) name:AVAudioSessionRouteChangeNotification object:nil];
    [center addObserver:self selector:@selector(audioReset:) name:AVAudioSessionMediaServicesWereResetNotification object:nil];
    [self controllersChanged:nil];
    [self updateRunning];
}
- (void)emitState {
    NSString* status = _error ?: [NSString stringWithFormat:@DEMO_TITLE " · %@", _running ? @"Playing" : @"Paused"];
    NSString* diagnostics = [NSString stringWithFormat:@"frames=%u;pad=%u;lastTouch=%u;observed=%u;touchEvents=%u;running=%d;muted=%d;audio=%u;dropped=%u;underrun=%u;controllers=%d",
        _frames, unsigned(_touchPad | _controllerPad), unsigned(_lastTouch), unsigned(PlayerCore::lastInput()),
        _touchEvents, _running, _muted, _audio.renderedFrames, _audio.droppedFrames, _audio.underrunFrames, _controller != nil];
    if (self.stateChanged) self.stateChanged(status, diagnostics);
}
- (void)applyInput { PlayerCore::buttons(_running ? (_touchPad | _controllerPad) : 0); }
- (void)press:(UIButton*)button {
    if (!_running) return;
    _touchPad |= button.tag; _lastTouch = button.tag; ++_touchEvents;
    button.backgroundColor = UIColor.systemBlueColor;
    [self applyInput]; [self emitState];
}
- (void)release:(UIButton*)button {
    _touchPad &= ~button.tag;
    button.backgroundColor = [UIColor colorWithWhite:0.15 alpha:1];
    [self applyInput]; [self emitState];
}
- (void)clearInput {
    _touchPad = _controllerPad = 0;
    for (UIButton* button in _buttons) button.backgroundColor = [UIColor colorWithWhite:0.15 alpha:1];
    PlayerCore::buttons(0);
}
- (void)setUserPaused:(BOOL)value { _userPaused = value; [self updateRunning]; }
- (BOOL)userPaused { return _userPaused; }
- (void)setApplicationActive:(BOOL)value { _applicationActive = value; [self updateRunning]; }
- (BOOL)applicationActive { return _applicationActive; }
- (void)setMuted:(BOOL)value { _muted = value; _audio.muted = value; [self emitState]; }
- (BOOL)muted { return _muted; }
- (void)updateRunning {
    BOOL run = _ready && !_closed && _applicationActive && !_userPaused && !_interrupted;
    if (run != _running) {
        _running = run;
        _clock.paused = !run;
        _timing.reset();
        [self clearInput];
        if (run) {
            NSError* error = nil;
            if (![_audio start:&error]) _error = [@"Audio unavailable: " stringByAppendingString:error.localizedDescription ?: @"engine setup failed"];
            else _error = nil;
        } else [_audio stop];
    }
    [self emitState];
}
- (void)controllersChanged:(NSNotification*)note {
    _controller.extendedGamepad.valueChangedHandler = nil;
    _controller = nil;
    for (GCController* controller in GCController.controllers) {
        if (controller.extendedGamepad) { _controller = controller; break; }
    }
    _controllerPad = 0; [self applyInput];
    if (_controller) {
        _controller.handlerQueue = dispatch_get_main_queue();
        __weak BJGPlayerController* weakSelf = self;
        _controller.extendedGamepad.valueChangedHandler = ^(GCExtendedGamepad* pad, GCControllerElement* element) {
            [weakSelf readController];
        };
    }
    [self emitState];
}
- (void)readController {
    if (!_running) return;
    GCExtendedGamepad* pad = _controller.extendedGamepad;
    ControllerInput input;
    if (pad) {
        input.x = pad.leftThumbstick.xAxis.value; input.y = pad.leftThumbstick.yAxis.value;
        input.up = pad.dpad.up.pressed; input.down = pad.dpad.down.pressed;
        input.left = pad.dpad.left.pressed; input.right = pad.dpad.right.pressed;
        input.south = pad.buttonA.pressed; input.east = pad.buttonB.pressed;
        input.west = pad.buttonX.pressed; input.north = pad.buttonY.pressed;
        input.l = pad.leftShoulder.pressed; input.r = pad.rightShoulder.pressed;
        input.start = pad.buttonMenu.pressed; input.select = pad.buttonOptions.pressed;
    }
    _controllerPad = input.mask(); [self applyInput];
}
- (void)audioInterruption:(NSNotification*)note {
    auto type = [note.userInfo[AVAudioSessionInterruptionTypeKey] unsignedIntegerValue];
    _interrupted = type == AVAudioSessionInterruptionTypeBegan;
    if (!_interrupted && !([note.userInfo[AVAudioSessionInterruptionOptionKey] unsignedIntegerValue] & AVAudioSessionInterruptionOptionShouldResume)) _userPaused = YES;
    [self updateRunning];
}
- (void)audioRouteChanged:(NSNotification*)note {
    auto reason = [note.userInfo[AVAudioSessionRouteChangeReasonKey] unsignedIntegerValue];
    if (reason != AVAudioSessionRouteChangeReasonNewDeviceAvailable && reason != AVAudioSessionRouteChangeReasonOldDeviceUnavailable) return;
    if (!_running) return;
    [_audio stop];
    NSError* error = nil;
    if (![_audio start:&error]) _error = error.localizedDescription;
    [self emitState];
}
- (void)audioReset:(NSNotification*)note {
    [_audio stop]; _audio = [BJGAudioOutput new]; _audio.muted = _muted;
    _running = NO; [self updateRunning];
}
- (void)tick:(CADisplayLink*)clock {
    if (!_running) return;
    [self readController];
    auto count = _timing.advance(clock.timestamp);
    for (unsigned i = 0; i < count; ++i) { PlayerCore::frame(); ++_frames; }
    [_audio pumpOffline];
    [_screen draw];
    if (_frames % 6 == 0) [self emitState];
}

- (void)mtkView:(MTKView*)view drawableSizeWillChange:(CGSize)size {}
- (void)drawInMTKView:(MTKView*)view {
    unsigned w = PlayerCore::width(), h = PlayerCore::height();
    if (!w || !h) return;
    if (!_texture || _texture.width != w || _texture.height != h) {
        // Core pixels are 0x00RRGGBB: little-endian ARM64 memory is B,G,R,0.
        // The fragment shader supplies opaque alpha independently.
        MTLTextureDescriptor* d = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatBGRA8Unorm width:w height:h mipmapped:NO];
        d.usage = MTLTextureUsageShaderRead;
        _texture = [view.device newTextureWithDescriptor:d];
    }
    [_texture replaceRegion:MTLRegionMake2D(0,0,w,h) mipmapLevel:0 withBytes:PlayerCore::pixels() bytesPerRow:PlayerCore::pitch()*4];
    MTLRenderPassDescriptor* pass = view.currentRenderPassDescriptor;
    id<CAMetalDrawable> drawable = view.currentDrawable;
    if (!pass || !drawable) return;
    id<MTLCommandBuffer> command = [_queue commandBuffer];
    id<MTLRenderCommandEncoder> encoder = [command renderCommandEncoderWithDescriptor:pass];
    [encoder setRenderPipelineState:_pipeline];
    [encoder setFragmentTexture:_texture atIndex:0];
    [encoder drawPrimitives:MTLPrimitiveTypeTriangleStrip vertexStart:0 vertexCount:4];
    [encoder endEncoding];
    [command presentDrawable:drawable];
    // One texture: wait before CPU writes the next frame into it.
    [command commit];
    [command waitUntilCompleted];
}

- (void)shutdown {
    if (_closed) return;
    _closed = YES;
    [_clock invalidate]; _clock = nil;
    [_audio stop];
    _controller.extendedGamepad.valueChangedHandler = nil;
    [NSNotificationCenter.defaultCenter removeObserver:self];
    PlayerCore::stop(); _ready = _running = NO;
}
- (void)dealloc { [self shutdown]; }
+ (void)runSelfTest {
    dispatch_async(dispatch_get_main_queue(), ^{
        NSDictionary* audio = [BJGAudioOutput verifyOfflineRendering];
        bool loaded = loadDemo();
        for (int i = 0; loaded && i < DEMO_FRAMES; ++i) PlayerCore::frame();
        int word = PlayerCore::wramWord(DEMO_OFFSET);
        bool lit = false;
        for (unsigned y = 0; y < PlayerCore::height(); ++y)
            for (unsigned x = 0; x < PlayerCore::width(); ++x)
                lit |= (PlayerCore::pixels()[y * PlayerCore::pitch() + x] & 0xffffff) != 0;
        bool pass = loaded && word == DEMO_WANT && lit && [audio[@"pass"] boolValue];
        NSDictionary* result = @{@"pass": @(pass), @"frames": @(DEMO_FRAMES), @"wram": @(word), @"expected": @(DEMO_WANT), @"nonblack": @(lit), @"audio": audio};
        NSString* path = [NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES).firstObject stringByAppendingPathComponent:@"selfcheck.json"];
        [[NSJSONSerialization dataWithJSONObject:result options:NSJSONWritingPrettyPrinted error:nil] writeToFile:path atomically:YES];
        NSLog(@"BJG_SELFCHECK %@", result);
        PlayerCore::stop();
        exit(pass ? 0 : 1);
    });
}
@end
