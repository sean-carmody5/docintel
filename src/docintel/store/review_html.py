"""A self-contained review page: one calm list, detail on demand, the source beside it.

One row per quotation line: product, price, and at most one short note saying what
needs a person. Opening a row shows the fields on the left and the document on the
right: the page image for scans and PDFs, or the text with the evidence quotes
highlighted. Reasons and scores sit behind "Show details". Decisions are kept in the
browser and exported as JSON for `docintel approve --decisions`. No server, no build
step, nothing fetched from the network; page previews are files next to the page.
"""

from __future__ import annotations

import json
from typing import Any

from docintel.reconcile import Conflict, Duplicate
from docintel.records import KEY_FIELDS, Record
from docintel.verify.confidence import ESSENTIAL

FIELD_ORDER = (
    "product_name",
    "inn",
    "strength",
    "dosage_form",
    "units_per_pack",
    "uom",
    "price_per_uom",
    "price_per_pack",
    "currency",
    "discount_pct",
    "quantity",
    "extended_amount",
    "moq_packs",
    "lead_time_days",
    "quotation_ref",
    "incoterm",
    "document_date",
    "valid_until",
)

STYLE = """
:root{--bg:#fcfcfc;--fg:#1a1a1a;--muted:#6f6f6f;--faint:#a3a3a3;--line:#ebebeb;--soft:#f4f4f4;--hover:#f7f7f7;
--btn:#1a1a1a;--btn-fg:#ffffff;--amber:#b7791f;--red:#c0392b;--green:#2f7d4f;--mark:#fff1c2;
--sans:-apple-system,BlinkMacSystemFont,"Segoe UI Variable Text","Segoe UI",Roboto,Helvetica,Arial,sans-serif;--mono:ui-monospace,Consolas,"SFMono-Regular",monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#111111;--fg:#ededed;--muted:#9a9a9a;--faint:#666666;--line:#262626;
--soft:#1a1a1a;--hover:#171717;--btn:#ededed;--btn-fg:#111111;--amber:#e0a84a;--red:#f07167;--green:#5fbf87;--mark:#4a3b10;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#111111;--fg:#ededed;--muted:#9a9a9a;--faint:#666666;--line:#262626;--soft:#1a1a1a;--hover:#171717;
--btn:#ededed;--btn-fg:#111111;--amber:#e0a84a;--red:#f07167;--green:#5fbf87;--mark:#4a3b10;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 var(--sans);-webkit-font-smoothing:antialiased}
.page{max-width:1180px;margin:0 auto;padding:40px 24px 80px}
.num{font-variant-numeric:tabular-nums}code{font:12px var(--mono);white-space:nowrap}
button{font:inherit;color:inherit;background:none;border:0;padding:0;cursor:pointer}button:disabled{cursor:default;opacity:.4}
.btn{height:32px;padding:0 14px;border:1px solid var(--line);border-radius:6px;background:var(--bg);font-weight:500}
.btn:hover{background:var(--hover)}.btn.primary{background:var(--btn);color:var(--btn-fg);border-color:var(--btn)}.btn.primary:hover{opacity:.88}
.btn.on{background:var(--btn);color:var(--btn-fg);border-color:var(--btn)}
button:focus-visible,input:focus-visible,select:focus-visible,.row:focus-visible{outline:2px solid var(--fg);outline-offset:2px}
input,select{font:inherit;color:inherit;background:var(--bg);border:1px solid var(--line);border-radius:6px;height:32px;padding:0 10px;min-width:0;max-width:100%}
select{appearance:none;-webkit-appearance:none;padding-right:26px;background-image:linear-gradient(45deg,transparent 50%,var(--muted) 50%),linear-gradient(135deg,var(--muted) 50%,transparent 50%);background-position:right 13px top 13px,right 9px top 13px;background-size:4px 4px,4px 4px;background-repeat:no-repeat}
.hd{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;margin-bottom:28px}
h1{font-size:22px;font-weight:600;letter-spacing:-.01em;margin:0 0 4px}.sub{margin:0;color:var(--muted)}
.hd-r{position:relative;display:flex;align-items:center;gap:16px;padding-top:6px}
.help{width:24px;height:24px;border-radius:50%;border:1px solid var(--line);color:var(--muted);font-size:13px;font-weight:500;line-height:1;display:inline-flex;align-items:center;justify-content:center}.help:hover,.help.on{color:var(--fg);border-color:var(--fg)}
.prog{display:flex;flex-direction:column;align-items:flex-end;gap:6px;color:var(--muted);font-size:13px}
.prog i{display:block;width:140px;height:3px;background:var(--line);border-radius:2px;overflow:hidden}.prog i b{display:block;height:100%;background:var(--fg);transition:width .2s}
.helpbox{position:absolute;top:44px;right:0;z-index:5;width:400px;max-width:calc(100vw - 32px);padding:18px 20px;background:var(--bg);border:1px solid var(--line);border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.08);font-size:13px;text-align:left}
.helpbox[hidden]{display:none}.helpbox h3{margin:0 0 8px;font-size:13px;font-weight:600}.helpbox p{margin:0 0 8px;color:var(--muted)}.helpbox p b{color:var(--fg);font-weight:600}.helpbox .sec+.sec{margin-top:16px}
.helpbox .ind{display:inline-block;vertical-align:middle;margin:-2px 6px 0 0}.helpbox .ind.none{border:1px solid var(--faint)}
.helpbox table{border-collapse:collapse}.helpbox td{padding:3px 12px 3px 0;vertical-align:top;color:var(--muted)}.helpbox td:first-child{white-space:nowrap}
.helpbox kbd{font:inherit;font-size:12px;padding:0 6px;border:1px solid var(--line);border-radius:4px;color:var(--fg);background:var(--soft)}
.helpbox .x{position:absolute;top:10px;right:12px;color:var(--faint);font-size:16px}.helpbox .x:hover{color:var(--fg)}
.tabs{display:flex;gap:22px;border-bottom:1px solid var(--line);margin-bottom:18px}
.tabs button{padding:8px 0 10px;color:var(--muted);border-bottom:2px solid transparent;margin-bottom:-1px}
.tabs button span{color:var(--faint);margin-left:6px}.tabs button.on{color:var(--fg);border-bottom-color:var(--fg)}.tabs button:hover{color:var(--fg)}
.bar{display:flex;gap:10px;margin-bottom:10px}.bar[hidden]{display:none}.bar input{flex:1;min-width:0}
.rec{border-bottom:1px solid var(--line)}.rec:first-child{border-top:1px solid var(--line)}
.row{display:grid;grid-template-columns:14px minmax(0,1fr) minmax(0,240px) 170px 90px;gap:16px;align-items:center;padding:14px 10px;cursor:pointer;border-radius:8px;margin:0 -10px}
.row:hover{background:var(--hover)}.rec.open .row{background:var(--soft)}
.ind{width:8px;height:8px;border-radius:50%;justify-self:center}.ind.amber{background:var(--amber)}.ind.red{background:var(--red)}
.name{font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.meta{color:var(--muted);font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.issue{font-size:13px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.issue.red{color:var(--red)}.issue.amber{color:var(--amber)}
.price{text-align:right;white-space:nowrap}.price b{font-weight:500;font-size:15px}.price span{color:var(--muted);font-size:13px;margin-left:4px}.price small{display:block;color:var(--faint);font-size:12px}
.dec{text-align:right;font-size:13px;color:var(--muted)}.dec.approve{color:var(--green)}.dec.reject{color:var(--red)}.dec.hold{color:var(--amber)}
.detail{display:grid;grid-template-columns:minmax(0,1fr) minmax(300px,440px);gap:36px;padding:6px 10px 26px 40px}.detail.solo{grid-template-columns:1fr}
.actions{display:flex;align-items:center;gap:8px;margin:10px 0 18px}.actions .hint{margin-left:auto;color:var(--faint);font-size:12px}
.why{margin:0 0 18px;padding:12px 14px;border-left:2px solid var(--amber);background:var(--soft);border-radius:0 6px 6px 0}
.why.red{border-left-color:var(--red)}.why p{margin:0}.why p+p{margin-top:4px}
.fields{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:18px 24px;margin:0}
.f dt{font-size:12px;color:var(--muted);margin-bottom:2px}.f dd{margin:0;font-weight:500}.f dd em{font-style:normal;color:var(--faint);font-weight:400}.f dd .u{color:var(--muted);font-weight:400;font-size:13px}
.f.flag dd{color:var(--amber)}.f.sev dd{color:var(--red)}.f.flag dd em,.f.sev dd em{color:inherit}
.f small{display:block;font-size:12px;color:var(--muted);margin-top:3px;font-weight:400}.f small.ev{color:var(--faint);font-style:italic}.f small.sc{color:var(--faint)}
.more{margin-top:18px;color:var(--muted);font-size:13px;text-decoration:underline;text-underline-offset:3px}.more:hover{color:var(--fg)}
.extra{margin-top:18px;color:var(--muted);font-size:13px}.extra p{margin:4px 0}.extra b{color:var(--fg);font-weight:500}
.src{margin-top:10px;min-width:0}.sh{display:flex;align-items:center;gap:14px;font-size:13px;color:var(--muted);margin-bottom:8px;min-height:24px}
.sh .sn{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--fg);font-weight:500}
.stabs button{color:var(--muted);padding:0 2px 2px;border-bottom:2px solid transparent;margin-left:10px}.stabs button.on{color:var(--fg);border-bottom-color:var(--fg)}
.pnav{display:inline-flex;align-items:center;gap:8px;white-space:nowrap}.pnav button{width:22px;height:22px;border:1px solid var(--line);border-radius:4px;font-size:14px;line-height:1}
.pg{display:block;width:100%;height:auto;border:1px solid var(--line);border-radius:6px;cursor:zoom-in;background:#fff}
.txt{position:relative;margin:0;max-height:560px;overflow:auto;padding:12px 14px;border:1px solid var(--line);border-radius:6px;font:12px/1.55 var(--mono);white-space:pre-wrap;word-break:break-word;color:var(--muted)}
.txt mark{background:var(--mark);color:var(--fg);border-radius:2px;padding:0 1px}
.lb{position:fixed;inset:0;z-index:20;background:#0f0f0f;display:flex;flex-direction:column}.lb[hidden]{display:none}
.lbbar{display:flex;align-items:center;gap:6px;padding:8px 14px;color:#ddd;font-size:13px}.lbbar .n{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lbbar button{min-width:30px;height:30px;padding:0 10px;border:1px solid #3a3a3a;border-radius:6px;color:#eee;font-size:14px;line-height:1}.lbbar button:hover{background:#2a2a2a}.lbbar button[hidden]{display:none}.lbbar .pct{min-width:48px;text-align:center;font-variant-numeric:tabular-nums}
.lbview{flex:1;overflow:auto;cursor:grab;position:relative}.lbview.drag{cursor:grabbing}.lbview img{display:block;max-width:none;background:#fff;margin:16px auto;user-select:none;-webkit-user-drag:none}
.lbhint{position:fixed;bottom:12px;left:0;right:0;text-align:center;color:#888;font-size:12px;pointer-events:none}
.empty{padding:48px 0;color:var(--muted);text-align:center}
.cmp h2{font-size:15px;font-weight:600;margin:26px 0 10px}.cmp h2:first-child{margin-top:4px}
.cmp table{width:100%;border-collapse:collapse;margin-bottom:6px}.cmp th{text-align:left;font-weight:500;color:var(--muted);font-size:13px;padding:8px 10px;border-bottom:1px solid var(--line)}
.cmp td{padding:10px;border-bottom:1px solid var(--line)}.cmp .r{text-align:right}.cmp caption{text-align:left;font-weight:500;padding:0 0 8px;caption-side:top}
.cmp .note{color:var(--muted);font-size:13px;margin:0 0 22px}
.out{width:100%;height:140px;font:12px/1.4 var(--mono);margin-top:12px;border:1px solid var(--line);border-radius:6px;padding:10px}
@media (max-width:900px){.detail{grid-template-columns:1fr}}
@media (max-width:760px){.page{padding:24px 16px 60px}.row{grid-template-columns:14px minmax(0,1fr) auto}.issue,.dec{display:none}.price small{display:none}.detail{padding-left:10px}.hd{flex-direction:column}.hd-r{padding:0;flex-wrap:wrap}.prog{align-items:flex-start}.helpbox{right:auto;left:0}.bar{flex-wrap:wrap}.bar input{flex:1 1 100%}.bar select{flex:1 1 40%;min-width:0;max-width:100%}.fields{grid-template-columns:repeat(auto-fill,minmax(140px,1fr))}}
"""

SCRIPT = r"""
(function(){
const D=window.__DATA__,R=D.records,SRC=D.sources||{};
const KEY='docintel-decisions-'+(D.run.started||'run');let dec={};try{dec=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const S={view:'review',q:'',doc:'',sort:'confidence',open:null,more:{},page:{},tab:{}};
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const LABEL={product_name:'Product',inn:'INN',strength:'Strength',dosage_form:'Form',uom:'Unit',units_per_pack:'Units per pack',price_per_uom:'Unit price',price_per_pack:'Pack price',currency:'Currency',discount_pct:'Discount',quantity:'Quantity',extended_amount:'Extended amount',moq_packs:'Minimum order (packs)',lead_time_days:'Lead time (days)',quotation_ref:'Reference',incoterm:'Incoterm',document_date:'Document date',valid_until:'Valid until'};
const label=f=>LABEL[f]||f.replace(/_/g,' ');
const money=v=>v==null||v===''?'':(typeof v==='number'?v.toLocaleString('en-GB',{maximumFractionDigits:v<1?4:v<100?3:2}):esc(v));
const date=v=>{const m=/^(\d{4})-(\d{2})-(\d{2})$/.exec(String(v));return m?new Date(Date.UTC(+m[1],+m[2]-1,+m[3])).toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}):esc(v)};
const fmt=(f,v)=>f==='discount_pct'&&typeof v==='number'?money(v)+'%':/_date$|^valid_until$/.test(f)?date(v):typeof v==='number'?money(v):esc(v);
const grp=r=>(r.status==='failed'||r.status==='no_lines')?'failed':(r.needs_review?'review':'clean');
const docOf=r=>r.parent_document||r.source_document;
const docId=r=>r.source_id||String(r.record_id).split(':')[0];
const UNREAD=/could not (be )?read/;
const REWRITE=[[/^model could not read this field$/,'could not be read'],[/^value not found in the source text$/,'not found verbatim in the text'],[/^not found by \w+$/,'not confirmed by OCR'],[/^agrees with (.+), confidence lifted$/,'matches the copy in $1'],[/^stated in weeks$/,'converted from weeks']];
const plain=s=>{for(const [re,to] of REWRITE){if(re.test(s))return s.replace(re,to)}return s};
const cap=s=>s.charAt(0).toUpperCase()+s.slice(1);
function human(x){const m=/^([a-z_]+): (.*)$/.exec(x);if(m&&LABEL[m[1]])return label(m[1])+' '+plain(m[2]);let s=x;for(const f in LABEL)s=s.replace(new RegExp('\\b'+f+'\\b','g'),LABEL[f].toLowerCase());return cap(s)}
const reasons=r=>(r.review_reasons||[]).map(human);
const RE_ESC=t=>t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const BY_LEN=Object.keys(LABEL).sort((a,b)=>LABEL[b].length-LABEL[a].length);
function flaggedFields(r){const out=new Set();for(const x of r.review_reasons||[]){let t=x.toLowerCase();for(const f of BY_LEN){const tok=new RegExp('\\b'+f+'\\b'),lab=new RegExp('\\b'+RE_ESC(LABEL[f].toLowerCase())+'\\b');if(tok.test(t)||lab.test(t)){out.add(f);t=t.replace(tok,' ').replace(lab,' ')}}}return out}
const severe=r=>grp(r)==='failed'||(r.review_reasons||[]).some(x=>UNREAD.test(x))||D.essential.some(f=>r[f]==null);
function issue(r){if(grp(r)==='failed')return'Could not load';if(!r.needs_review)return'';const rs=reasons(r);if(!rs.length)return'Check';if(rs.length===1)return rs[0];return rs.length+' things to check'}
function visible(){const q=S.q.toLowerCase();let rows=R.filter(r=>(S.view==='all'||grp(r)===S.view)&&(!S.doc||docOf(r)===S.doc)&&(!q||[r.source_document,r.supplier_name,r.product_name,r.inn,r.quotation_ref,r.currency].join(' ').toLowerCase().includes(q)));
 if(S.sort==='confidence')rows.sort((a,b)=>a.overall_confidence-b.overall_confidence||docOf(a).localeCompare(docOf(b))||(a.line_no||0)-(b.line_no||0));
 else if(S.sort==='document')rows.sort((a,b)=>docOf(a).localeCompare(docOf(b))||(a.line_no||0)-(b.line_no||0));
 else if(S.sort==='price')rows.sort((a,b)=>(b.price_per_uom||0)-(a.price_per_uom||0));
 else rows.sort((a,b)=>(a.supplier_name||'').localeCompare(b.supplier_name||'')||(a.line_no||0)-(b.line_no||0));return rows}
function header(){const docs=new Set(R.map(docOf)).size,need=R.filter(r=>grp(r)==='review'),done=need.filter(r=>dec[r.record_id]).length;
 $('#sub').textContent=`${docs} documents, ${R.length} quotation lines, ${need.length} need a decision`;
 $('#progtxt').textContent=`${done} of ${need.length} decided`;$('#progbar').style.width=(need.length?Math.round(done/need.length*100):0)+'%';
 const c={review:0,clean:0,failed:0};R.forEach(r=>c[grp(r)]++);const cmp=(D.conflicts||[]).length+(D.duplicates||[]).length;
 $('#tabs').innerHTML=[['review','Needs review',c.review],['clean','Clean',c.clean],['failed','Failed',c.failed],['all','All',R.length],['compare','Comparisons',cmp]].filter(([k,,n])=>n||k==='review'||k==='all').map(([k,l,n])=>`<button class="${S.view===k?'on':''}" data-v="${k}">${l}<span>${n}</span></button>`).join('');
 document.querySelectorAll('#tabs button').forEach(b=>b.onclick=()=>{S.view=b.dataset.v;S.open=null;render()});
 const names=[...new Set(R.map(docOf))].sort();$('#doc').innerHTML=`<option value="">All documents</option>`+names.map(n=>`<option value="${esc(n)}"${S.doc===n?' selected':''}>${esc(n)}</option>`).join('')}
function rowHtml(r){const d=dec[r.record_id]||'',sv=severe(r),g=grp(r),is=issue(r);const tone=g==='failed'||(g==='review'&&sv)?'red':g==='review'?'amber':'';
 const meta=[r.inn?esc(r.inn)+(r.strength?' '+esc(r.strength):''):'',esc(r.supplier_name||''),esc(docOf(r))].filter(Boolean).join(' · ');
 const price=r.price_per_uom!=null?`<b>${money(r.price_per_uom)}</b><span>${esc(r.currency||'')}</span><small>per ${esc(r.uom||'unit')}${r.units_per_pack!=null?' · '+money(r.units_per_pack)+' per pack':''}</small>`:r.price_per_pack!=null?`<b>${money(r.price_per_pack)}</b><span>${esc(r.currency||'')}</span><small>per pack</small>`:`<span>${g==='failed'?'':'no price'}</span>`;
 const decided=d==='approve'?'Approved':d==='hold'?'On hold':d==='reject'?'Rejected':'';
 return`<article class="rec${S.open===r.record_id?' open':''}" data-id="${esc(r.record_id)}"><div class="row" tabindex="0"><span class="ind ${tone}"></span><div><div class="name">${esc(r.product_name||(g==='failed'?r.source_document:'(no product name)'))}</div><div class="meta">${meta}</div></div><div class="issue ${tone}">${esc(is)}</div><div class="price num">${price}</div><div class="dec ${d}">${decided}</div></div>${S.open===r.record_id?detail(r):''}</article>`}
function highlight(text,evidence){const qs=Object.entries(evidence).filter(([,q])=>typeof q==='string'&&q.trim().length>=3).sort((a,b)=>b[1].length-a[1].length);const low=text.toLowerCase();const ranges=[];
 for(const [f,q] of qs){const ql=q.toLowerCase();let i=0,k=0;while(k<20&&(i=low.indexOf(ql,i))!==-1){ranges.push([i,i+ql.length,f]);i+=ql.length;k++}}
 ranges.sort((a,b)=>a[0]-b[0]);const merged=[];for(const x of ranges){const l=merged[merged.length-1];if(l&&x[0]<=l[1])l[1]=Math.max(l[1],x[1]);else merged.push(x.slice())}
 let out='',pos=0;for(const [a,b,f] of merged){out+=esc(text.slice(pos,a))+'<mark data-f="'+esc(f)+'">'+esc(text.slice(a,b))+'</mark>';pos=b}return out+esc(text.slice(pos))}
function sourcePanel(r){const s=SRC[docId(r)];if(!s)return'';const hasPages=!!(s.pages&&s.pages.length),hasText=!!s.text;if(!hasPages&&!hasText)return'';
 const tab=S.tab[r.record_id]||(hasPages?'page':'text');const n=hasPages?s.pages.length:0;const pi=Math.min(S.page[r.record_id]||0,Math.max(n-1,0));
 const tabs=hasPages&&hasText?`<span class="stabs"><button class="${tab==='page'?'on':''}" data-stab="page">Page</button><button class="${tab==='text'?'on':''}" data-stab="text">Text</button></span>`:'';
 const nav=tab==='page'&&n>1?`<span class="pnav"><button data-pg="-1"${pi===0?' disabled':''}>&lsaquo;</button><span class="num">${pi+1} of ${n}</span><button data-pg="1"${pi===n-1?' disabled':''}>&rsaquo;</button></span>`:'';
 const body=tab==='page'&&hasPages?`<img class="pg" src="${esc(s.pages[pi])}" alt="${esc(s.name)}, page ${pi+1}" data-zoom>`:`<pre class="txt">${highlight(s.text,r.evidence||{})}</pre>`;
 return`<aside class="src"><div class="sh"><span class="sn" title="${esc(s.path)}">${esc(s.name)}</span>${tabs}${nav}</div>${body}</aside>`}
function detail(r){const d=dec[r.record_id]||'',rs=reasons(r),more=!!S.more[r.record_id],c=r.confidence||{},ev=r.evidence||{},sv=severe(r);
 const flagged=flaggedFields(r);
 const fields=D.field_order.filter(f=>f in r&&(r[f]!=null||D.essential.includes(f)||flagged.has(f)||more));
 const cells=fields.map(f=>{const v=r[f],x=c[f],miss=v==null,rr=x?(x.reasons||[]).map(plain):[],unread=rr.some(s=>UNREAD.test(s));
  const hot=flagged.has(f)||D.essential.includes(f),sev=hot&&(miss||unread),flag=!sev&&flagged.has(f);
  const val=miss?`<em>${unread?'unreadable':'not stated'}</em>`:fmt(f,v)+(f==='price_per_uom'&&r.uom?` <span class="u">per ${esc(r.uom)}</span>`:'');
  const note=more&&rr.length?`<small>${esc(rr.join(' · '))}</small>`:'';
  const quote=(flag||more)&&ev[f]?`<small class="ev">“${esc(ev[f])}”</small>`:'';
  const score=more&&x?`<small class="sc">confidence ${x.score.toFixed(2)}</small>`:'';
  return`<div class="f${flag?' flag':''}${sev?' sev':''}"><dt>${label(f)}</dt><dd>${val}</dd>${note}${quote}${score}</div>`}).join('');
 const conflicts=(D.conflicts||[]).filter(x=>x.record_ids.includes(r.record_id));
 const extra=[r.superseded?`<p><b>Corrected in the document:</b> ${label(r.superseded.field).toLowerCase()} ${money(r.superseded.old)} became ${money(r.superseded.new)}${r.superseded.reason?' ('+esc(r.superseded.reason)+')':''}</p>`:'',
  r.price_tiers?`<p><b>Volume tiers:</b> ${r.price_tiers.map(t=>money(t.min_packs)+(t.max_packs!=null?'–'+money(t.max_packs):'+')+' packs at '+money(t.price_per_pack)).join(', ')}</p>`:'',
  conflicts.map(x=>`<p><b>Also quoted by</b> ${esc(x.suppliers.filter(s=>s!==r.supplier_name).join(', '))}: ${esc(x.note)}</p>`).join(''),
  (r.notes||[]).length&&more?`<p><b>Notes:</b> ${r.notes.map(esc).join(' ')}</p>`:'',
  more?`<p>${esc(docOf(r))}${r.parent_document?' › '+esc(r.source_document):''} · ${esc(r.source_locator||'')} · ${esc(r.record_id)}${r.quotation_ref?' · ref '+esc(r.quotation_ref):''}</p>`:''].join('');
 const src=sourcePanel(r);
 return`<div class="detail${src?'':' solo'}"><div><div class="actions"><button class="btn${d==='approve'?' on':d?'':' primary'}" data-d="approve">${d==='approve'?'Approved':'Approve'}</button><button class="btn${d==='hold'?' on':''}" data-d="hold">${d==='hold'?'On hold':'Hold'}</button><button class="btn${d==='reject'?' on':''}" data-d="reject">${d==='reject'?'Rejected':'Reject'}</button><span class="hint">A, H, R · J and K to move</span></div>
 ${rs.length?`<div class="why${sv?' red':''}">${rs.map(x=>`<p>${esc(x)}</p>`).join('')}</div>`:''}
 <dl class="fields">${cells}</dl>
 ${extra?`<div class="extra">${extra}</div>`:''}
 <button class="more" data-more>${more?'Hide details':'Show details'}</button></div>${src}</div>`}
function compare(){const cs=D.conflicts||[],ds=D.duplicates||[];if(!cs.length&&!ds.length)return'<div class="empty">Nothing to compare: every product came from one supplier, and no quotation arrived twice.</div>';
 let h='<div class="cmp">';
 if(cs.length){h+='<h2>Quoted by more than one supplier</h2>'+cs.map(c=>`<table><caption>${esc(c.inn_normalised)} ${esc(c.strength||'')} ${esc(c.form||'')}</caption><thead><tr><th>Supplier</th><th class="r">Pack</th><th class="r">Unit price</th><th>Currency</th></tr></thead><tbody>${c.suppliers.map((s,i)=>`<tr><td>${esc(s)}</td><td class="r num">${money(c.units_per_pack[i])} ${esc(c.uoms[i])}</td><td class="r num">${money(c.unit_prices[i])}</td><td>${esc(c.currencies[i])}</td></tr>`).join('')}</tbody></table><p class="note">${esc(c.note)}</p>`).join('')}
 if(ds.length){h+='<h2>Same quotation, more than one file</h2>'+ds.map(d=>`<p><b>${esc(d.supplier||'')}</b> ${esc(d.quotation_ref)}: ${d.documents.map(esc).join(', ')}</p><p class="note">${d.matched_lines} lines matched, ${d.agreements} values agree${d.disagreements.length?', '+d.disagreements.length+' differ: '+d.disagreements.map(x=>label(x.field).toLowerCase()+' on '+esc(x.product||'')).join('; '):''}.</p>`).join('')}
 return h+'</div>'}
function render(){header();const el=$('#list');$('#bar').hidden=S.view==='compare';
 if(S.view==='compare'){el.innerHTML=compare();return}
 const rows=visible();if(!rows.length){el.innerHTML='<div class="empty">Nothing here.</div>';return}
 el.innerHTML=rows.map(rowHtml).join('');
 el.querySelectorAll('.row').forEach(x=>{const id=x.parentElement.dataset.id;x.onclick=()=>{S.open=S.open===id?null:id;render()};x.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();x.onclick()}}});
 el.querySelectorAll('.actions button').forEach(b=>b.onclick=()=>decide(S.open,b.dataset.d));
 el.querySelectorAll('[data-more]').forEach(b=>b.onclick=()=>{S.more[S.open]=!S.more[S.open];render()});
 el.querySelectorAll('[data-stab]').forEach(b=>b.onclick=()=>{S.tab[S.open]=b.dataset.stab;render()});
 el.querySelectorAll('[data-pg]').forEach(b=>b.onclick=()=>{S.page[S.open]=(S.page[S.open]||0)+Number(b.dataset.pg);render()});
 el.querySelectorAll('[data-zoom]').forEach(i=>i.onclick=()=>lbOpen(S.open));
 const pre=el.querySelector('.rec.open .txt');if(pre){const m=pre.querySelector('mark[data-f="product_name"]')||pre.querySelector('mark[data-f="price_per_uom"]')||pre.querySelector('mark[data-f="inn"]')||pre.querySelector('mark');if(m)pre.scrollTop=Math.max(0,m.offsetTop-pre.clientHeight/3)}
 const open=el.querySelector('.rec.open');if(open)open.scrollIntoView({block:'nearest'})}
function decide(id,d){if(!id)return;if(dec[id]===d)delete dec[id];else dec[id]=d;try{localStorage.setItem(KEY,JSON.stringify(dec))}catch(e){}render()}
function help(on){$('#helpbox').hidden=!on;$('#help').classList.toggle('on',on);if(on)try{localStorage.setItem('docintel-help-seen','1')}catch(e){}}
document.addEventListener('keydown',e=>{if(/INPUT|TEXTAREA|SELECT/.test(e.target.tagName))return;
 if(e.key==='Escape'){if(!$('#lb').hidden)$('#lb').hidden=true;else if(!$('#helpbox').hidden)help(false);else{S.open=null;render()}return}
 if(!$('#lb').hidden){if(e.key==='+'||e.key==='=')lbZoom(1.25);else if(e.key==='-')lbZoom(0.8);else if(e.key==='0')lbFit();else if(e.key==='ArrowLeft')$('#lbprev').click();else if(e.key==='ArrowRight')$('#lbnext').click();e.preventDefault();return}
 if(S.view==='compare')return;const rows=visible();const i=rows.findIndex(r=>r.record_id===S.open);
 if(e.key==='j'||e.key==='ArrowDown'){if(i<rows.length-1){S.open=rows[i+1].record_id;render()}e.preventDefault()}
 else if(e.key==='k'||e.key==='ArrowUp'){S.open=i>0?rows[i-1].record_id:null;render();e.preventDefault()}
 else if(S.open&&(e.key==='a'||e.key==='h'||e.key==='r'))decide(S.open,{a:'approve',h:'hold',r:'reject'}[e.key])});
const LB={id:null,scale:1,fit:true};const lbImg=$('#lbimg'),lbView=$('#lbview');
function lbSrc(){const r=R.find(x=>x.record_id===LB.id);const s=r&&SRC[docId(r)];return s&&s.pages&&s.pages.length?s:null}
function lbOpen(id){LB.id=id;if(!lbSrc())return;LB.fit=true;$('#lb').hidden=false;lbShow()}
function lbShow(){const s=lbSrc();if(!s)return;const n=s.pages.length,pi=Math.min(S.page[LB.id]||0,n-1);$('#lbname').textContent=s.name;$('#lbpage').textContent=n>1?`${pi+1} of ${n}`:'';$('#lbprev').hidden=$('#lbnext').hidden=n<2;$('#lbprev').disabled=pi===0;$('#lbnext').disabled=pi===n-1;
 lbImg.onload=()=>{if(LB.fit)lbFit();else lbApply()};lbImg.src=s.pages[pi]}
function lbFit(){LB.fit=true;LB.scale=Math.min(1,(lbView.clientWidth-32)/lbImg.naturalWidth);lbApply()}
function lbApply(){lbImg.style.width=Math.round(lbImg.naturalWidth*LB.scale)+'px';$('#lbpct').textContent=Math.round(LB.scale*100)+'%'}
function lbZoom(factor,cx,cy){const old=LB.scale;LB.scale=Math.min(6,Math.max(0.1,old*factor));LB.fit=false;const rect=lbView.getBoundingClientRect();const ax=cx==null?rect.width/2:cx-rect.left,ay=cy==null?rect.height/2:cy-rect.top;const x=ax+lbView.scrollLeft,y=ay+lbView.scrollTop;const k=LB.scale/old;lbApply();lbView.scrollLeft=x*k-ax;lbView.scrollTop=y*k-ay}
lbView.addEventListener('wheel',e=>{e.preventDefault();lbZoom(e.deltaY<0?1.15:1/1.15,e.clientX,e.clientY)},{passive:false});
lbView.addEventListener('dblclick',e=>{if(LB.scale<1)lbZoom(1/LB.scale,e.clientX,e.clientY);else lbFit()});
let drag=null;lbView.addEventListener('mousedown',e=>{if(e.button)return;drag={x:e.clientX,y:e.clientY,l:lbView.scrollLeft,t:lbView.scrollTop};lbView.classList.add('drag');e.preventDefault()});
window.addEventListener('mousemove',e=>{if(!drag)return;lbView.scrollLeft=drag.l-(e.clientX-drag.x);lbView.scrollTop=drag.t-(e.clientY-drag.y)});
window.addEventListener('mouseup',()=>{drag=null;lbView.classList.remove('drag')});
document.querySelectorAll('[data-lz]').forEach(b=>b.onclick=()=>lbZoom(b.dataset.lz==='1'?1.25:0.8));
$('#lbfit').onclick=lbFit;$('#lb100').onclick=()=>{LB.fit=false;LB.scale=1;lbApply()};$('#lbx').onclick=()=>{$('#lb').hidden=true};
$('#lbprev').onclick=()=>{S.page[LB.id]=Math.max(0,(S.page[LB.id]||0)-1);lbShow();render()};$('#lbnext').onclick=()=>{S.page[LB.id]=(S.page[LB.id]||0)+1;lbShow();render()};
window.addEventListener('resize',()=>{if(!$('#lb').hidden&&LB.fit)lbFit()});
$('#help').onclick=e=>{e.stopPropagation();help($('#helpbox').hidden)};$('#helpx').onclick=()=>help(false);
document.addEventListener('click',e=>{if(!$('#helpbox').hidden&&!$('#helpbox').contains(e.target))help(false)});
try{if(!localStorage.getItem('docintel-help-seen'))help(true)}catch(e){}
$('#q').oninput=e=>{S.q=e.target.value;render()};$('#doc').onchange=e=>{S.doc=e.target.value;render()};$('#sort').onchange=e=>{S.sort=e.target.value;render()};
$('#export').onclick=()=>{const payload=JSON.stringify({run:D.run.started,decisions:dec},null,2);const btn=$('#export');const ok=()=>{btn.textContent='Copied';setTimeout(()=>btn.textContent='Export decisions',1600)};
 const show=()=>{$('#out').hidden=false;$('#out').value=payload};if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(payload).then(ok).catch(show);else show()};
render();
})();
"""

HELP = """<div id="helpbox" class="helpbox" hidden><button class="x" id="helpx" aria-label="Close">&times;</button>
<div class="sec"><h3>What the marks mean</h3>
<p><span class="ind red"></span><b>Red.</b> This line cannot be used yet. Something you need to price it (the product, the INN, the unit price or the currency) could not be read from the document, or was not in it. Open it, look at the source, then reject or hold it.</p>
<p><span class="ind amber"></span><b>Amber.</b> The values are there, but one of them was reached in a way that deserves a human look. The usual reasons: the unit price was calculated from the pack price; the document corrected a value further down; the price depends on quantity and the lowest tier is shown; a value does not appear word for word in the document, so it could not be confirmed automatically.</p>
<p><span class="ind none"></span><b>No mark.</b> Every key value appears word for word in the document and passed the checks. Approve without opening, or spot-check.</p></div>
<div class="sec"><h3>Keys</h3><table><tr><td><kbd>J</kbd></td><td>open the next line</td></tr><tr><td><kbd>K</kbd></td><td>open the previous line, or close the one at the top</td></tr><tr><td><kbd>A</kbd> <kbd>H</kbd> <kbd>R</kbd></td><td>approve, hold or reject the open line</td></tr><tr><td><kbd>Esc</kbd></td><td>close the open line, the zoomed page, or this help</td></tr><tr><td><kbd>+</kbd> <kbd>&minus;</kbd> <kbd>0</kbd></td><td>zoom the page in, out, or back to fit (the scroll wheel zooms too)</td></tr></table></div>
<div class="sec"><h3>Decisions</h3><p><b>Approve</b> sends the line on, <b>Hold</b> keeps it for later, <b>Reject</b> drops it. Decisions stay in this browser until you press <b>Export decisions</b>, which copies them as JSON for <code>docintel approve --decisions</code>.</p></div></div>"""


def _record_payload(r: Record) -> dict[str, Any]:
    d = r.model_dump(mode="json")
    d["confidence"] = {k: v.model_dump() for k, v in r.confidence.items()}
    d["flags"] = [f.model_dump() for f in r.flags]
    return d


def render_review_html(
    records: list[Record],
    conflicts: list[Conflict],
    duplicates: list[Duplicate],
    run: dict[str, Any],
    *,
    sources: list[dict[str, Any]] | None = None,
    standalone: bool = True,
) -> str:
    data = {
        "run": {
            k: (v if isinstance(v, str | int | float | bool) or v is None else str(v))
            for k, v in run.items()
        },
        "records": [_record_payload(r) for r in records],
        "conflicts": [c.model_dump() for c in conflicts],
        "duplicates": [d.model_dump() for d in duplicates],
        "sources": {s["id"]: s for s in sources or []},
        "field_order": list(FIELD_ORDER),
        "key_fields": list(KEY_FIELDS),
        "essential": list(ESSENTIAL),
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    body = f"""<title>Quotation Review</title>
<style>{STYLE}</style>
<main class="page">
<header class="hd"><div><h1>Quotation review</h1><p class="sub" id="sub"></p></div>
<div class="hd-r"><button id="help" class="help" aria-label="How to read this page">?</button><div class="prog"><span id="progtxt"></span><i><b id="progbar"></b></i></div><button id="export" class="btn primary">Export decisions</button>{HELP}</div></header>
<nav class="tabs" id="tabs"></nav>
<div class="bar" id="bar"><input id="q" type="search" placeholder="Search products, suppliers or documents"><select id="doc"></select><select id="sort"><option value="confidence">Least certain first</option><option value="document">By document</option><option value="supplier">By supplier</option><option value="price">Highest unit price</option></select></div>
<section id="list"></section>
<textarea id="out" class="out" hidden></textarea>
</main>
<div id="lb" class="lb" hidden><div class="lbbar"><span class="n" id="lbname"></span><button id="lbprev" title="Previous page">&lsaquo;</button><span id="lbpage"></span><button id="lbnext" title="Next page">&rsaquo;</button><span style="width:10px"></span><button data-lz="-1" title="Zoom out">&minus;</button><span class="pct" id="lbpct"></span><button data-lz="1" title="Zoom in">+</button><button id="lbfit" title="Fit to window">Fit</button><button id="lb100" title="Actual size">100%</button><button id="lbx" title="Close">&times;</button></div><div class="lbview" id="lbview"><img id="lbimg" alt="Page, full size"></div><div class="lbhint">Scroll to zoom, drag to pan, double-click to toggle. Esc closes.</div></div>
<script>window.__DATA__={payload};</script>
<script>{SCRIPT}</script>
"""
    if not standalone:
        return body
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n</head>\n<body>\n'
        + body
        + "</body>\n</html>\n"
    )
