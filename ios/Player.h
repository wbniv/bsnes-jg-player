#import <UIKit/UIKit.h>
NS_ASSUME_NONNULL_BEGIN
@interface BJGPlayerController : UIViewController
@property(nonatomic) BOOL userPaused;
@property(nonatomic) BOOL applicationActive;
@property(nonatomic) BOOL muted;
@property(nonatomic, copy, nullable) void (^stateChanged)(NSString* status, NSString* diagnostics);
- (void)shutdown;
+ (void)runSelfTest;
@end
NS_ASSUME_NONNULL_END
