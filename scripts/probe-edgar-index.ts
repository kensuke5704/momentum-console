const UA = process.env.SEC_USER_AGENT ?? "MomentumConsole/2.0 kensuke5704@users.noreply.github.com";
const urls = [
  "https://www.sec.gov/Archives/edgar/daily-index/2026/QTR3/master.20260731.idx",
  "https://www.sec.gov/Archives/edgar/daily-index/2026/QTR3/form.20260731.idx",
  "https://www.sec.gov/Archives/edgar/data/850027/000085002726000015/primary_doc.xml",
];
async function main() {
  for (const url of urls) {
    try {
      const res = await fetch(url,{headers:{"User-Agent":UA,"Accept":"text/plain,application/xml,*/*"},redirect:"follow",signal:AbortSignal.timeout(30000)});
      const buf=await res.arrayBuffer();
      const text=new TextDecoder().decode(buf.slice(0,2000));
      console.log(JSON.stringify({url,status:res.status,contentType:res.headers.get("content-type"),length:buf.byteLength,containsNport:/NPORT-P/i.test(text),prefix:text.slice(0,500)}));
    } catch(e) { console.log(JSON.stringify({url,error:String(e)})); }
  }
}
main().catch((error)=>{console.error(error);process.exitCode=1});
