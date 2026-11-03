/* iRECEIPT portable binary integrity verifier, OpenSSL 3.
 * Verifies exact domain-separated canonical bytes, SHA-256 receipt ID and
 * Ed25519 signature independently of Python crypto. No JSON semantic validation,
 * operator trust enrollment, hardware attestation, or production authority.
 * Usage: native_receipt_verify message.bin PUBKEY_HEX SIGNATURE_HEX sha256:HASH
 */
#include <openssl/evp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const unsigned char DOMAIN[] = {
  'i','R','E','C','E','I','P','T','/','h','a','r','d','w','a','r','e','-',
  'n','e','u','t','r','a','l','/','v','1',0
};
static int nibble(char c) {
  if (c >= '0' && c <= '9') return c-'0';
  if (c >= 'a' && c <= 'f') return c-'a'+10;
  return -1;
}
static int parse_hex(const char *in, unsigned char *out, size_t n) {
  if (!in || strlen(in)!=n*2) return 0;
  for (size_t i=0;i<n;i++) {
    int a=nibble(in[2*i]), b=nibble(in[2*i+1]);
    if(a<0 || b<0)return 0;
    out[i]=(unsigned char)((a<<4)|b);
  }
  return 1;
}
int main(int argc, char **argv) {
  if(argc!=5) {fputs("usage: native_receipt_verify message.bin pubkey sig receipt_id\n",stderr); return 2;}
  unsigned char key[32],signature[64],expected[32],actual[32];
  if(!parse_hex(argv[2],key,32) || !parse_hex(argv[3],signature,64) ||
      strncmp(argv[4],"sha256:",7)!=0 || !parse_hex(argv[4]+7,expected,32)) {
    fputs("REJECT:invalid_key_signature_or_id\n",stderr);return 2;
  }
  FILE *f=fopen(argv[1],"rb");
  if(!f){fputs("REJECT:file_missing\n",stderr);return 2;}
  if(fseek(f,0,SEEK_END)!=0){fclose(f);return 2;}
  long length=ftell(f);
  if(length<(long)sizeof(DOMAIN) || length>8*1024*1024) {fclose(f);fputs("REJECT:length\n",stderr);return 2;}
  rewind(f);
  unsigned char *msg=malloc((size_t)length);
  if(!msg){fclose(f);return 2;}
  int rc=2;
  if(fread(msg,1,(size_t)length,f)!=(size_t)length || memcmp(msg,DOMAIN,sizeof(DOMAIN))!=0){
    fputs("REJECT:domain_or_read\n",stderr);goto cleanup;
  }
  unsigned int digest_len=0;
  if(EVP_Digest(msg,(size_t)length,actual,&digest_len,EVP_sha256(),NULL)!=1 ||
      digest_len!=32 || memcmp(expected,actual,32)!=0){
    fputs("REJECT:receipt_sha256\n",stderr);goto cleanup;
  }
  EVP_PKEY *pub=EVP_PKEY_new_raw_public_key(EVP_PKEY_ED25519,NULL,key,32);
  EVP_MD_CTX *ctx=EVP_MD_CTX_new();
  if(!pub || !ctx) {fputs("REJECT:openssl_context\n",stderr);goto done;}
  if(EVP_DigestVerifyInit(ctx,NULL,NULL,NULL,pub)!=1 ||
     EVP_DigestVerify(ctx,signature,64,msg,(size_t)length)!=1){
    fputs("REJECT:ed25519_signature\n",stderr);goto done;
  }
  puts("PASS:NATIVE_OPENSSL_SIGNATURE_AND_HASH_ONLY");
  rc=0;
done:
  EVP_MD_CTX_free(ctx);EVP_PKEY_free(pub);
cleanup:
  free(msg);fclose(f);
  return rc;
}
