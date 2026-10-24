#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "ibare_ffi.h"

#define WIDTH 256
#define HEIGHT 256
#define CHANNELS 3
#define FIXED_TIMESTAMP 1711210000ULL

typedef struct { float x, y, z; } vec3;
typedef struct { vec3 origin, dir; } ray;

static vec3 add(vec3 a, vec3 b){ return (vec3){a.x+b.x,a.y+b.y,a.z+b.z}; }
static vec3 sub(vec3 a, vec3 b){ return (vec3){a.x-b.x,a.y-b.y,a.z-b.z}; }
static vec3 mul(vec3 a,float s){ return (vec3){a.x*s,a.y*s,a.z*s}; }
static float dot(vec3 a,vec3 b){ return a.x*b.x+a.y*b.y+a.z*b.z; }
static vec3 norm(vec3 a){ float l=sqrtf(dot(a,a)); return mul(a,1.0f/l); }

static int hit_sphere(ray r, vec3 c, float radius, float *t){
    vec3 oc=sub(r.origin,c);
    float b=2.0f*dot(oc,r.dir);
    float cc=dot(oc,oc)-radius*radius;
    float d=b*b-4.0f*cc;
    if(d<0.0f) return 0;
    *t=(-b-sqrtf(d))*0.5f;
    return *t>0.0f;
}

static void render(uint8_t *fb){
    vec3 cam={0,0,-5}, sphere={0,0,0}, light=norm((vec3){1,1,-1});
    for(int y=0;y<HEIGHT;y++) for(int x=0;x<WIDTH;x++){
        float px=((float)x/(float)WIDTH)*2.0f-1.0f;
        float py=((float)y/(float)HEIGHT)*2.0f-1.0f;
        ray r={cam,norm((vec3){px,py,1.0f})};
        float t; size_t i=((size_t)y*WIDTH+(size_t)x)*CHANNELS;
        if(hit_sphere(r,sphere,1.0f,&t)){
            vec3 p=add(r.origin,mul(r.dir,t));
            float intensity=fmaxf(0.0f,dot(norm(sub(p,sphere)),light));
            fb[i]=(uint8_t)(intensity*255.0f);
            fb[i+1]=(uint8_t)(intensity*100.0f);
            fb[i+2]=(uint8_t)(intensity*50.0f);
        } else { fb[i]=10; fb[i+1]=10; fb[i+2]=20; }
    }
}

static void hex32(const uint8_t in[32], char out[65]){
    static const char h[]="0123456789abcdef";
    for(size_t i=0;i<32;i++){out[i*2]=h[in[i]>>4];out[i*2+1]=h[in[i]&15];}
    out[64]='\0';
}

int main(void){
    const size_t n=(size_t)WIDTH*HEIGHT*CHANNELS;
    uint8_t *fb=(uint8_t*)malloc(n);
    uint8_t frame_hash[32], receipt[32];
    char frame_hex[65], receipt_hex[65];
    if(!fb) return 2;
    render(fb);
    if(ibare_hash_bytes(fb,n,frame_hash)!=0){free(fb);return 3;}
    ibare_receipt_manifest m={0};
    m.sequence_id=1; m.timestamp_utc=FIXED_TIMESTAMP;
    for(size_t i=0;i<32;i++) m.payload_hash[i]=frame_hash[i];
    m.platform_flags=ibare_detect_architecture_flags();
    if(ibare_generate_deterministic_receipt(&m,receipt)!=0){free(fb);return 4;}
    hex32(frame_hash,frame_hex); hex32(receipt,receipt_hex);
    printf("algorithm=deterministic-ray-tracing\n");
    printf("framebuffer_sha256=%s\n",frame_hex);
    printf("process_receipt=%s\n",receipt_hex);
    printf("physical_gate=ACTION_REQUIRED\n");
    free(fb); return 0;
}
