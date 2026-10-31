#import <Foundation/Foundation.h>
NS_ASSUME_NONNULL_BEGIN
@interface BJGAudioOutput : NSObject
@property(nonatomic) BOOL muted;
@property(nonatomic, readonly) uint32_t renderedFrames;
@property(nonatomic, readonly) uint32_t droppedFrames;
@property(nonatomic, readonly) uint32_t underrunFrames;
- (BOOL)start:(NSError**)error;
- (void)stop;
- (void)pumpOffline;
+ (NSDictionary*)verifyOfflineRendering;
@end
NS_ASSUME_NONNULL_END
