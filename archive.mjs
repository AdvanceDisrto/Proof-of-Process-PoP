/* Bounded local-only TAR/GZIP reader. No extraction to filesystem; no links. */
const text=new TextDecoder('utf-8',{fatal:true});
const demand=(c,m)=>{if(!c)throw Error(m)};
const decode=b=>text.decode(b.subarray(0,b.indexOf(0)<0?b.length:b.indexOf(0)));
const octal=b=>{const s=decode(b).trim();demand(/^[0-7]+$/.test(s),'bad tar number');return parseInt(s,8)};
export function parseTar(bytes){
 demand(bytes instanceof Uint8Array&&bytes.length<=24000000,'oversize tar');
 const files=Object.create(null);let pos=0,count=0,closed=false;
 while(pos+512<=bytes.length){
  const h=bytes.slice(pos,pos+512);
  if(h.every(b=>b===0)){closed=true;break;}
  const check=octal(h.slice(148,156));
  let actual=0;for(let i=0;i<512;i++)actual+=(i>=148&&i<156)?32:h[i];
  demand(check===actual,'tar checksum mismatch');
  demand(h[156]===0||h[156]===48,'unsupported tar member type');
  const name=decode(h.slice(0,100));
  demand(/^[A-Za-z0-9._/-]{1,96}$/.test(name)&&!name.startsWith('/')&&!name.includes('..')&&!name.includes('//'),'unsafe tar path');
  const len=octal(h.slice(124,136));const from=pos+512,to=from+len;
  demand(len<=24000000&&to<=bytes.length,'tar entry exceeds limits');
  demand(!(name in files),'duplicate tar path');
  files[name]=bytes.slice(from,to);count++;demand(count<=64,'too many tar entries');
  pos=from+Math.ceil(len/512)*512;
 }
 demand(closed,'tar terminator missing');
 return files;
}
export async function readBundleArchive(file){
 demand(file.size<=24000000,'compressed evidence oversize');
 demand(typeof DecompressionStream==='function','gzip unavailable in browser');
 const reader=file.stream().pipeThrough(new DecompressionStream('gzip')).getReader();
 const chunks=[];let total=0;
 try{
  for(;;){const {value,done}=await reader.read();if(done)break;
   total+=value.length;demand(total<=24000000,'expanded evidence oversize');chunks.push(value);}
 }catch(error){await reader.cancel().catch(()=>{});throw error;}
 const data=new Uint8Array(total);let offset=0;
 for(const c of chunks){data.set(c,offset);offset+=c.length;}
 const files=parseTar(data);
 demand(files['POP_SIGNED_RECEIPT.json']!==undefined,'signed receipt missing');
 return {bundle:JSON.parse(text.decode(files['POP_SIGNED_RECEIPT.json'])),files};
}
