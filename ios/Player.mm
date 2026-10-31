#import <UIKit/UIKit.h>
#import <MetalKit/MetalKit.h>
#include "CoreHost.hpp"
#include "DemoConfig.h"
#include <algorithm>

static bool loadDemo() {
    NSBundle* bundle = NSBundle.mainBundle;
    return PlayerCore::load([[bundle pathForResource:@"demo" ofType:@"sfc"] UTF8String],
                           [[bundle.resourcePath stringByAppendingPathComponent:@"Database"] UTF8String]);
}

@interface PlayerViewController : UIViewController <MTKViewDelegate>
@end
@implementation PlayerViewController {
    MTKView* _screen;
    UILabel* _status;
    CADisplayLink* _clock;
    id<MTLCommandQueue> _queue;
    id<MTLRenderPipelineState> _pipeline;
    id<MTLTexture> _texture;
    double _last, _credit;
    uint16_t _pad;
    BOOL _ready;
}
- (void)viewDidLoad {
    [super viewDidLoad];
    self.view.backgroundColor = UIColor.blackColor;
    _status = [UILabel new];
    _status.textColor = UIColor.whiteColor;
    _status.textAlignment = NSTextAlignmentCenter;
    _status.numberOfLines = 2;
    _status.font = [UIFont preferredFontForTextStyle:UIFontTextStyleHeadline];
    _status.text = @DEMO_TITLE " · iOS preview\nAudio output is not yet implemented";
    _status.translatesAutoresizingMaskIntoConstraints = NO;
    [self.view addSubview:_status];
    id<MTLDevice> device = MTLCreateSystemDefaultDevice();
    _screen = [[MTKView alloc] initWithFrame:CGRectZero device:device];
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
    UIStackView* controls = [UIStackView new];
    controls.axis = UILayoutConstraintAxisHorizontal;
    controls.spacing = 4;
    controls.distribution = UIStackViewDistributionFillEqually;
    controls.translatesAutoresizingMaskIntoConstraints = NO;
    NSArray* labels = @[@"↑", @"↓", @"←", @"→", @"B", @"A", @"Start", @"Select"];
    const int bits[] = {11, 10, 9, 8, 15, 7, 12, 13};
    NSArray* names = @[@"Up", @"Down", @"Left", @"Right", @"B", @"A", @"Start", @"Select"];
    for (NSUInteger i = 0; i < labels.count; ++i) {
        UIButton* button = [UIButton buttonWithType:UIButtonTypeSystem];
        [button setTitle:labels[i] forState:UIControlStateNormal];
        button.accessibilityLabel = names[i];
        button.backgroundColor = [UIColor colorWithWhite:0.15 alpha:1];
        button.tag = 1 << bits[i];
        [button addTarget:self action:@selector(press:) forControlEvents:UIControlEventTouchDown];
        [button addTarget:self action:@selector(release:) forControlEvents:UIControlEventTouchUpInside | UIControlEventTouchUpOutside | UIControlEventTouchCancel | UIControlEventTouchDragExit];
        [controls addArrangedSubview:button];
    }
    [self.view addSubview:controls];
    UILayoutGuide* safe = self.view.safeAreaLayoutGuide;
    NSLayoutConstraint* preferredWidth = [_screen.widthAnchor constraintEqualToAnchor:safe.widthAnchor constant:-24];
    preferredWidth.priority = UILayoutPriorityDefaultHigh;
    [NSLayoutConstraint activateConstraints:@[
        [_status.topAnchor constraintEqualToAnchor:safe.topAnchor constant:8],
        [_status.leadingAnchor constraintEqualToAnchor:safe.leadingAnchor constant:12],
        [_status.trailingAnchor constraintEqualToAnchor:safe.trailingAnchor constant:-12],
        [_screen.topAnchor constraintEqualToAnchor:_status.bottomAnchor constant:12],
        [_screen.centerXAnchor constraintEqualToAnchor:safe.centerXAnchor],
        [_screen.widthAnchor constraintLessThanOrEqualToAnchor:safe.widthAnchor constant:-24],
        [_screen.widthAnchor constraintEqualToAnchor:_screen.heightAnchor multiplier:4.0/3.0],
        preferredWidth,
        [_screen.bottomAnchor constraintLessThanOrEqualToAnchor:controls.topAnchor constant:-12],
        [controls.leadingAnchor constraintEqualToAnchor:safe.leadingAnchor constant:8],
        [controls.trailingAnchor constraintEqualToAnchor:safe.trailingAnchor constant:-8],
        [controls.heightAnchor constraintEqualToConstant:48],
        [controls.bottomAnchor constraintEqualToAnchor:safe.bottomAnchor constant:-12]
    ]];
    _ready = _pipeline && loadDemo();
    if (!_ready) { _status.text = error.localizedDescription ?: @"Could not load the bundled ROM"; return; }
    _clock = [CADisplayLink displayLinkWithTarget:self selector:@selector(tick:)];
    [_clock addToRunLoop:NSRunLoop.mainRunLoop forMode:NSRunLoopCommonModes];
    [NSNotificationCenter.defaultCenter addObserver:self selector:@selector(pause) name:UIApplicationWillResignActiveNotification object:nil];
    [NSNotificationCenter.defaultCenter addObserver:self selector:@selector(resume) name:UIApplicationDidBecomeActiveNotification object:nil];
}
- (void)press:(UIButton*)button { _pad |= button.tag; PlayerCore::buttons(_pad); }
- (void)release:(UIButton*)button { _pad &= ~button.tag; PlayerCore::buttons(_pad); }
- (void)pause { _clock.paused = YES; _last = _credit = 0; _pad = 0; PlayerCore::buttons(0); }
- (void)resume { _last = _credit = 0; _clock.paused = NO; }
- (void)tick:(CADisplayLink*)clock {
    if (!_ready) return;
    if (_last == 0) { _last = clock.timestamp; return; }
    _credit = std::min(_credit + clock.timestamp - _last, 3.0/60.0988);
    _last = clock.timestamp;
    while (_credit >= 1.0/60.0988) { PlayerCore::frame(); _credit -= 1.0/60.0988; }
    [_screen draw];
}
- (void)mtkView:(MTKView*)view drawableSizeWillChange:(CGSize)size {}
- (void)drawInMTKView:(MTKView*)view {
    unsigned w = PlayerCore::width(), h = PlayerCore::height();
    if (!w || !h) return;
    if (!_texture || _texture.width != w || _texture.height != h) {
        MTLTextureDescriptor* d = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm width:w height:h mipmapped:NO];
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
@end

@interface AppDelegate : UIResponder <UIApplicationDelegate>
@property(nonatomic, strong) UIWindow* window;
@end
@implementation AppDelegate
- (BOOL)application:(UIApplication*)app didFinishLaunchingWithOptions:(NSDictionary*)options {
    self.window = [[UIWindow alloc] initWithFrame:UIScreen.mainScreen.bounds];
    if ([NSProcessInfo.processInfo.arguments containsObject:@"--self-test"]) {
        self.window.rootViewController = [UIViewController new];
        [self.window makeKeyAndVisible];
        dispatch_async(dispatch_get_main_queue(), ^{
            bool loaded = loadDemo();
            for (int i = 0; loaded && i < DEMO_FRAMES; ++i) PlayerCore::frame();
            int word = PlayerCore::wramWord(DEMO_OFFSET);
            bool lit = false;
            for (unsigned y = 0; y < PlayerCore::height(); ++y)
                for (unsigned x = 0; x < PlayerCore::width(); ++x)
                    lit |= (PlayerCore::pixels()[y * PlayerCore::pitch() + x] & 0xffffff) != 0;
            bool pass = loaded && word == DEMO_WANT && lit;
            NSDictionary* result = @{@"pass": @(pass), @"frames": @(DEMO_FRAMES), @"wram": @(word), @"expected": @(DEMO_WANT), @"nonblack": @(lit), @"width": @(PlayerCore::width()), @"height": @(PlayerCore::height())};
            NSString* path = [NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES).firstObject stringByAppendingPathComponent:@"selfcheck.json"];
            [[NSJSONSerialization dataWithJSONObject:result options:NSJSONWritingPrettyPrinted error:nil] writeToFile:path atomically:YES];
            NSLog(@"BJG_SELFCHECK %@", result);
            PlayerCore::stop();
            exit(pass ? 0 : 1);
        });
    } else {
        self.window.rootViewController = [PlayerViewController new];
        [self.window makeKeyAndVisible];
    }
    return YES;
}
@end
int main(int argc, char** argv) {
    @autoreleasepool { return UIApplicationMain(argc, argv, nil, NSStringFromClass(AppDelegate.class)); }
}
