#include <algorithm>
#include <array>
#include <atomic>
#include <charconv>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <cstdlib>
#include <fcntl.h>
#include <functional>
#include <iostream>
#include <mutex>
#include <netinet/in.h>
#include <queue>
#include <string>
#include <sys/socket.h>
#include <thread>
#include <unordered_map>
#include <unistd.h>
#include <vector>
#if defined(__AVX2__)
#include <immintrin.h>
#elif defined(__ARM_NEON) || defined(__aarch64__)
#include <arm_neon.h>
#endif

struct SessionState { uint64_t last_nonce; std::chrono::steady_clock::time_point last_active; };
class SessionManager {
 std::unordered_map<std::string,SessionState> sessions; std::mutex mu;
public:
 bool validate_and_update(const std::string& id,uint64_t nonce){
  std::lock_guard<std::mutex> g(mu); auto now=std::chrono::steady_clock::now(); auto it=sessions.find(id);
  if(it!=sessions.end()){ if(nonce<=it->second.last_nonce)return false; it->second={nonce,now}; return true; }
  sessions.emplace(id,SessionState{nonce,now}); return true;
 }
};

struct EnergySample { bool available=false; uint64_t microjoules=0; };
class HardwareTelemetry {
 static EnergySample read_path(const char* path){
  int fd=open(path,O_RDONLY); if(fd<0)return {}; char buf[64]{}; ssize_t n=read(fd,buf,sizeof(buf)-1); close(fd);
  if(n<=0) return {};
  uint64_t v=0;
  auto result=std::from_chars(buf,buf+n,v);
  if(result.ec!=std::errc()) return {};
  return {true,v};
 }
public:
 static EnergySample read_rapl(){ return read_path("/sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj"); }
 static bool tpm_node_present(){ return access("/dev/tpmrm0",F_OK)==0 || access("/dev/tpm0",F_OK)==0; }
};

class SIMDProcessor {
public:
 static const char* backend(){
#if defined(__AVX2__)
  return "AVX2";
#elif defined(__ARM_NEON) || defined(__aarch64__)
  return "NEON";
#else
  return "SCALAR";
#endif
 }
 static void process(const uint8_t* in,uint8_t* out,size_t n){
  size_t i=0;
#if defined(__AVX2__)
  const __m256i mask=_mm256_set1_epi8(static_cast<char>(0xAA));
  for(;i+32<=n;i+=32){auto v=_mm256_loadu_si256(reinterpret_cast<const __m256i*>(in+i));v=_mm256_xor_si256(v,mask);_mm256_storeu_si256(reinterpret_cast<__m256i*>(out+i),v);}
#elif defined(__ARM_NEON) || defined(__aarch64__)
  const uint8x16_t mask=vdupq_n_u8(0xAA);
  for(;i+16<=n;i+=16){auto v=vld1q_u8(in+i);v=veorq_u8(v,mask);vst1q_u8(out+i,v);}
#endif
  for(;i<n;++i)out[i]=in[i]^0xAA;
 }
};

class ThreadPool {
 std::vector<std::thread> workers; std::queue<std::function<void()>> tasks; std::mutex mu; std::condition_variable cv; bool stop=false;
public:
 explicit ThreadPool(size_t n){n=std::max<size_t>(1,n);for(size_t i=0;i<n;++i)workers.emplace_back([this]{for(;;){std::function<void()> f;{std::unique_lock<std::mutex> l(mu);cv.wait(l,[this]{return stop||!tasks.empty();});if(stop&&tasks.empty())return;f=std::move(tasks.front());tasks.pop();}f();}});}
 template<class F> void enqueue(F&& f){{std::lock_guard<std::mutex> l(mu);tasks.emplace(std::forward<F>(f));}cv.notify_one();}
 ~ThreadPool(){{std::lock_guard<std::mutex> l(mu);stop=true;}cv.notify_all();for(auto& w:workers)w.join();}
};

SessionManager sessions;
static void send_all(int fd,const std::string& s){size_t off=0;while(off<s.size()){ssize_t n=send(fd,s.data()+off,s.size()-off,0);if(n<=0)break;off+=static_cast<size_t>(n);}}
static void handle_client(int fd){
 std::array<char,2048> b{}; ssize_t n=read(fd,b.data(),b.size()-1); if(n<=0){close(fd);return;}
 std::string req(b.data(),static_cast<size_t>(n)); uint64_t nonce=static_cast<uint64_t>(std::chrono::steady_clock::now().time_since_epoch().count());
 if(!sessions.validate_and_update("CLIENT_ALPHA",nonce)){send_all(fd,"HTTP/1.1 409 Conflict\r
Content-Length: 6\r
\r
replay");close(fd);return;}
 auto start=HardwareTelemetry::read_rapl(); bool tpm=HardwareTelemetry::tpm_node_present();
 std::vector<uint8_t> in(1<<20,0x55),out(in.size()); SIMDProcessor::process(in.data(),out.data(),in.size());
 auto end=HardwareTelemetry::read_rapl(); bool measured=start.available&&end.available&&end.microjoules>=start.microjoules;
 uint64_t delta=measured?end.microjoules-start.microjoules:0;
 std::string body="{\"state\":\"VERIFIED_PROCESS\",\"physical_gate\":\"ACTION_REQUIRED\",\"simd_backend\":\""+std::string(SIMDProcessor::backend())+"\",\"rapl_observed\":"+(measured?"true":"false")+",\"energy_delta_uj\":"+(measured?std::to_string(delta):"null")+",\"tpm_device_present\":"+(tpm?"true":"false")+",\"does_not_prove\":[\"TPM quote or hardware-rooted attestation\",\"RAPL calibration or workload-exclusive energy attribution\",\"fabricated custom silicon or foundry signoff\"]}";
 std::string h="HTTP/1.1 200 OK\r
Content-Type: application/json\r
Content-Length: "+std::to_string(body.size())+"\r
Connection: close\r
\r
"; send_all(fd,h+body); close(fd);
}
int main(int argc,char** argv){
 if(argc>1&&std::string(argv[1])=="--self-test"){std::vector<uint8_t> a(97,0x55),b(a.size());SIMDProcessor::process(a.data(),b.data(),a.size());if(!std::all_of(b.begin(),b.end(),[](uint8_t x){return x==0xff;}))return 2;SessionManager s;if(!s.validate_and_update("x",1)||s.validate_and_update("x",1)||!s.validate_and_update("x",2))return 3;std::cout<<"daemon self-test: PASS backend="<<SIMDProcessor::backend()<<"
";return 0;}
 int server=socket(AF_INET,SOCK_STREAM,0); if(server<0)return 1; int opt=1;setsockopt(server,SOL_SOCKET,SO_REUSEADDR,&opt,sizeof(opt));sockaddr_in a{};a.sin_family=AF_INET;a.sin_addr.s_addr=INADDR_ANY;a.sin_port=htons(8080);
 if(bind(server,reinterpret_cast<sockaddr*>(&a),sizeof(a))<0){perror("bind");return 1;}if(listen(server,SOMAXCONN)<0)return 1;ThreadPool pool(std::thread::hardware_concurrency());std::cout<<"iBare daemon listening 8080 SIMD="<<SIMDProcessor::backend()<<"
";
 for(;;){int fd=accept(server,nullptr,nullptr);if(fd>=0)pool.enqueue([fd]{handle_client(fd);});}
}
