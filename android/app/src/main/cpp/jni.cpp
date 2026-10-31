#include <jni.h>
#include <android/asset_manager.h>
#include <android/asset_manager_jni.h>
#include <android/log.h>
#include <bsnes.hpp>
#include <cpu.hpp>
#include <sfc.hpp>
#include <algorithm>
#include <cstdio>
#include <sstream>
#include <string>
#include <vector>
#include <chrono>
#include <atomic>
#include <pthread.h>

static AAssetManager* assets;
static std::vector<uint8_t> game;
static std::string gamePath;
// bsnes may provide 512-pixel hires frames even when the displayed frame is
// reduced to 256 pixels below. Keep the source framebuffer at the core's
// maximum width; the smaller destination buffer is only for converted RGBA.
static constexpr unsigned MaxVideoWidth = 512;
static constexpr unsigned MaxVideoHeight = 248;
static uint32_t pixels[MaxVideoWidth * MaxVideoHeight];
static uint8_t rgba[256 * 248 * 4];
static float audio[3200];
static unsigned rawWidth=0, rawHeight=0, rawPitch=0;
static uint16_t pad=0;
static bool loaded=false;
static std::atomic<bool> videoSampleReported{false};
static std::atomic<unsigned> nativeStepCount{0};
static std::atomic<unsigned> nativeLoadCount{0};
static void logcb(void*, int level, std::string& s) { if(level) __android_log_print(ANDROID_LOG_INFO,"bsnes", "%s",s.c_str()); }
static bool openStream(void*, std::string name, std::stringstream& out) {
  std::string path="Database/"+name; AAsset* a=AAssetManager_open(assets,path.c_str(),AASSET_MODE_BUFFER); if(!a)return false;
  const auto n=AAsset_getLength(a); std::string data((size_t)n,'\0'); AAsset_read(a,&data[0],(size_t)n); AAsset_close(a); out.write(data.data(),data.size()); return true;
}
static bool openVector(void*, std::string, std::vector<uint8_t>&){return false;}
static bool openMsu(void*, std::string, std::istream**){return false;}
static void writeCb(void*,std::string,const uint8_t*,unsigned){}
static bool loadRom(void*,unsigned id){if(id==Bsnes::GameType::SuperFamicom&&game.size()>=0x8000&&!gamePath.empty()){Bsnes::setRomSuperFamicom(game,gamePath);return true;}return false;}
static void video(const void*,unsigned w,unsigned h,unsigned p){rawWidth=w;rawHeight=h;rawPitch=p;bool expected=false;if(w&&h&&p&&videoSampleReported.compare_exchange_strong(expected,true)){unsigned lit=0,samples=0;for(unsigned y=0;y<h;y+=8)for(unsigned x=0;x<w;x+=8){samples++;if(pixels[y*p+x]&0xffffff)lit++;}__android_log_print(ANDROID_LOG_INFO,"BJG_TV_METRIC","{\"event\":\"native_video_sample\",\"width\":%u,\"height\":%u,\"pitch\":%u,\"lit_samples\":%u,\"samples\":%u,\"thread\":%lu}",w,h,p,lit,samples,(unsigned long)pthread_self());}}
static std::atomic<bool> audioCallbackSeen{false};
static void audioCb(const void*,size_t){
  if(!audioCallbackSeen.exchange(true)) __android_log_print(ANDROID_LOG_INFO,"BJG_NATIVE","discard-audio callback reached");
}
static int input(const void*,unsigned,unsigned){return pad;}
extern "C" JNIEXPORT jboolean JNICALL Java_org_bsnesjg_tv_NativeEngine_load(JNIEnv* env,jclass,jobject mgr,jbyteArray rom,jstring romName){
 const unsigned loadCall=nativeLoadCount.fetch_add(1)+1; const jsize n=env->GetArrayLength(rom); const char* name=env->GetStringUTFChars(romName,nullptr); const char* slug=name?name:"";
 __android_log_print(ANDROID_LOG_INFO,"BJG_NATIVE","engine_load_enter call=%u rom=%s bytes=%d loaded_before=%d thread=%lu",loadCall,slug,(int)n,loaded,(unsigned long)pthread_self());
 assets=AAssetManager_fromJava(env,mgr); if(loaded){Bsnes::unload();loaded=false;} videoSampleReported.store(false);nativeStepCount.store(0); if(n<0x8000){__android_log_print(ANDROID_LOG_ERROR,"BJG_NATIVE","engine_load_rejected call=%u reason=short-rom bytes=%d",loadCall,(int)n);if(name)env->ReleaseStringUTFChars(romName,name);return JNI_FALSE;}
 gamePath=slug;if(name)env->ReleaseStringUTFChars(romName,name);
 game.resize(n);env->GetByteArrayRegion(rom,0,n,reinterpret_cast<jbyte*>(game.data()));
 Bsnes::setOpenFileCallback(nullptr,openVector);Bsnes::setOpenStreamCallback(nullptr,openStream);Bsnes::setOpenMsuCallback(nullptr,openMsu);Bsnes::setRomLoadCallback(nullptr,loadRom);Bsnes::setWriteCallback(nullptr,writeCb);Bsnes::setLogCallback(nullptr,logcb);
 Bsnes::setAudioSpec({48000.0,(48000/60)<<1,0,audio,nullptr,&audioCb});Bsnes::setVideoSpec({pixels,nullptr,video});if(!Bsnes::load()){__android_log_print(ANDROID_LOG_ERROR,"BJG_NATIVE","engine_load_rejected call=%u reason=core-load-failed rom=%s",loadCall,gamePath.c_str());return JNI_FALSE;}
 Bsnes::setAudioSpec({48000.0,(48000/60)<<1,0,audio,nullptr,&audioCb});
 Bsnes::setInputSpec({0,Bsnes::Input::Device::Gamepad,nullptr,input});Bsnes::setInputSpec({1,Bsnes::Input::Device::Gamepad,nullptr,input});Bsnes::power();
 __android_log_print(ANDROID_LOG_INFO,"BJG_NATIVE","post-power cpu_thread=%p scheduler_active=%p",SuperFamicom::cpu.thread,SuperFamicom::scheduler.active);
 // Power/reset reconstructs the core's audio streams. Reattach the no-output
 // sink afterward so the first DSP frame cannot call a null frontend callback.
 __android_log_print(ANDROID_LOG_INFO,"BJG_NATIVE","reattach discard-audio callback=%p",reinterpret_cast<void*>(&audioCb));
 Bsnes::setAudioSpec({48000.0,(48000/60)<<1,0,audio,nullptr,&audioCb});
 Bsnes::setInputSpec({0,Bsnes::Input::Device::Gamepad,nullptr,input});Bsnes::setInputSpec({1,Bsnes::Input::Device::Gamepad,nullptr,input});
 __android_log_print(ANDROID_LOG_INFO,"BJG_NATIVE","engine_load_ready call=%u rom=%s thread=%lu cpu_thread=%p active=%p",loadCall,gamePath.c_str(),(unsigned long)pthread_self(),SuperFamicom::cpu.thread,SuperFamicom::scheduler.active);
 loaded=true;return JNI_TRUE;
}
extern "C" JNIEXPORT jboolean JNICALL Java_org_bsnesjg_tv_NativeEngine_isLoaded(JNIEnv*,jclass){return loaded?JNI_TRUE:JNI_FALSE;}
extern "C" JNIEXPORT void JNICALL Java_org_bsnesjg_tv_NativeEngine_step(JNIEnv*,jclass){if(!loaded)return;Bsnes::run();const unsigned n=nativeStepCount.fetch_add(1)+1;if(n<=3||n==30||n==60||n==61||n==120||n==600){__android_log_print(ANDROID_LOG_INFO,"BJG_NATIVE","step=%u pc=%06x cpu_clock=%lld ppu_v=%u event=%u cpu_thread=%p active=%p host=%p current=%p thread=%lu stp=%u wai=%u",n,SuperFamicom::cpu.r.pc.d,(long long)SuperFamicom::cpu.clock,SuperFamicom::ppu.vcounter(),(unsigned)SuperFamicom::scheduler.event,SuperFamicom::cpu.thread,SuperFamicom::scheduler.active,SuperFamicom::scheduler.host,co_active(),(unsigned long)pthread_self(),SuperFamicom::cpu.r.stp,SuperFamicom::cpu.r.wai);}}
extern "C" JNIEXPORT jlong JNICALL Java_org_bsnesjg_tv_NativeEngine_benchmark(JNIEnv*,jclass,jint frames){if(!loaded||frames<1||frames>60)return -1;auto start=std::chrono::steady_clock::now();for(int i=0;i<frames;i++)Bsnes::run();return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-start).count();}
extern "C" JNIEXPORT void JNICALL Java_org_bsnesjg_tv_NativeEngine_reset(JNIEnv*,jclass){if(loaded)Bsnes::reset();}
extern "C" JNIEXPORT void JNICALL Java_org_bsnesjg_tv_NativeEngine_setPad(JNIEnv*,jclass,jint value){pad=(uint16_t)value;}
static unsigned outputStep(){return rawWidth>=512?2:1;}
static unsigned outputYOff(){return rawHeight>=232?8:0;}
extern "C" JNIEXPORT jint JNICALL Java_org_bsnesjg_tv_NativeEngine_width(JNIEnv*,jclass){return rawWidth/outputStep();}
extern "C" JNIEXPORT jint JNICALL Java_org_bsnesjg_tv_NativeEngine_height(JNIEnv*,jclass){return std::min<unsigned>(224,rawHeight-outputYOff());}
extern "C" JNIEXPORT jint JNICALL Java_org_bsnesjg_tv_NativeEngine_pitch(JNIEnv*,jclass){return Java_org_bsnesjg_tv_NativeEngine_width(nullptr,nullptr);}
extern "C" JNIEXPORT void JNICALL Java_org_bsnesjg_tv_NativeEngine_copyPixels(JNIEnv* env,jclass,jobject target){auto* dst=static_cast<uint8_t*>(env->GetDirectBufferAddress(target));if(!dst)return;const unsigned step=outputStep(),yoff=outputYOff(),ow=rawWidth/step,oh=std::min<unsigned>(224,rawHeight-yoff);for(unsigned y=0;y<oh;y++)for(unsigned x=0;x<ow;x++){uint32_t c=pixels[(y+yoff)*rawPitch+x*step];size_t i=(y*ow+x)*4;dst[i]=c&255;dst[i+1]=(c>>8)&255;dst[i+2]=(c>>16)&255;dst[i+3]=255;}}
extern "C" JNIEXPORT jint JNICALL Java_org_bsnesjg_tv_NativeEngine_wramWord(JNIEnv*,jclass,jint off){auto m=Bsnes::getMemoryRaw(Bsnes::Memory::MainRAM);if(!m.first||off<0||(unsigned)(off+1)>=m.second)return -1;auto*p=(uint8_t*)m.first;return p[off]|(p[off+1]<<8);}
