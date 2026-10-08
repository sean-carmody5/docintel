"""A self-contained review workstation: the page a person actually works through.

Three panes: documents, records, detail. One visual carries the page: a confidence
strip per record, one cell per key field, so a reviewer sees which field is weak
before reading a number. No server, no build step, no network dependency beyond an
optional web font. Decisions are kept in the browser and copied out as JSON for
`docintel approve --decisions`.
"""

from __future__ import annotations

import json
from typing import Any

from docintel.reconcile import Conflict, Duplicate
from docintel.records import KEY_FIELDS, Record

FIELD_ORDER = (
    "product_name",
    "inn",
    "strength",
    "dosage_form",
    "uom",
    "units_per_pack",
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
STRIP_FIELDS = ("product_name", "inn", "strength", "units_per_pack", "price_per_uom", "currency")

STYLE = """
:root{--bg:#f2f4f6;--panel:#ffffff;--panel-2:#f8f9fa;--fg:#15202b;--muted:#5f6b78;--faint:#9aa5b1;--line:#dde2e8;
--accent:#0f5f74;--accent-fg:#ffffff;--sel:#e4eff3;--high:#2b7a4b;--medium:#9a6700;--low:#b4232c;--code:#eef1f4;
--sans:"IBM Plex Sans","Segoe UI",system-ui,-apple-system,sans-serif;--mono:"IBM Plex Mono",Consolas,"SFMono-Regular",monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0e1319;--panel:#151b22;--panel-2:#1a2129;--fg:#e4e9ee;--muted:#98a3ae;
--faint:#5f6a75;--line:#2a333d;--accent:#62b6cc;--accent-fg:#0b1216;--sel:#1b2b33;--high:#6fcf97;--medium:#e8b84a;--low:#f08a8f;--code:#0b1015;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0e1319;--panel:#151b22;--panel-2:#1a2129;--fg:#e4e9ee;--muted:#98a3ae;--faint:#5f6a75;--line:#2a333d;
--accent:#62b6cc;--accent-fg:#0b1216;--sel:#1b2b33;--high:#6fcf97;--medium:#e8b84a;--low:#f08a8f;--code:#0b1015;color-scheme:dark}
*{box-sizing:border-box}html,body{height:100%}body{margin:0;background:var(--bg);color:var(--fg);font:13.5px/1.45 var(--sans)}
button{font:inherit;color:inherit;background:none;border:1px solid var(--line);border-radius:3px;padding:4px 10px;cursor:pointer}
button:hover{border-color:var(--accent)}button:focus-visible,[tabindex]:focus-visible,input:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
input,select{font:inherit;color:inherit;background:var(--panel);border:1px solid var(--line);border-radius:3px;padding:5px 8px}
.mono{font-family:var(--mono)}.num{font-variant-numeric:tabular-nums}.muted{color:var(--muted)}.faint{color:var(--faint)}.sm{font-size:12px}
.app{display:grid;grid-template-rows:auto auto 1fr;height:100%;min-height:0}
.top{display:flex;align-items:baseline;gap:18px;padding:10px 18px;border-bottom:1px solid var(--line);background:var(--panel)}
.brand{font-weight:600;letter-spacing:.02em}.brand b{color:var(--accent);font-weight:600}.top .meta{color:var(--muted);font-size:12px;flex:1}
.progress{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted)}.progress i{display:inline-block;width:120px;height:4px;background:var(--line);border-radius:2px;overflow:hidden}
.progress i b{display:block;height:100%;background:var(--accent)}
.tools{display:flex;align-items:center;gap:14px;padding:8px 18px;border-bottom:1px solid var(--line);background:var(--panel);flex-wrap:wrap}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:3px;overflow:hidden}.seg button{border:0;border-right:1px solid var(--line);border-radius:0;padding:4px 11px}
.seg button:last-child{border-right:0}.seg button.on{background:var(--accent);color:var(--accent-fg)}.seg button span{opacity:.75;margin-left:5px;font-variant-numeric:tabular-nums}
.dist{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted);margin-left:auto}.dist i{display:inline-flex;width:160px;height:8px;border-radius:2px;overflow:hidden;background:var(--line)}
.dist i b{display:block;height:100%}.dist .k{display:inline-flex;gap:10px}.dist .k em{font-style:normal}.dot{display:inline-block;width:8px;height:8px;border-radius:2px;vertical-align:-1px;margin-right:4px}
.dot.high{background:var(--high)}.dot.medium{background:var(--medium)}.dot.low{background:var(--low)}
.panes{display:grid;grid-template-columns:250px minmax(420px,1fr) minmax(440px,560px);min-height:0}
.pane{min-height:0;overflow:auto;border-right:1px solid var(--line);background:var(--panel)}.pane:last-child{border-right:0;background:var(--panel-2)}
.ph{position:sticky;top:0;z-index:1;display:flex;align-items:center;gap:10px;padding:8px 12px;background:inherit;border-bottom:1px solid var(--line);font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.ph .tabs{display:inline-flex;gap:14px;text-transform:none;letter-spacing:0;font-size:13px}.ph .tabs button{border:0;padding:0 0 2px;border-radius:0;border-bottom:2px solid transparent;color:var(--muted)}
.ph .tabs button.on{color:var(--fg);border-bottom-color:var(--accent)}.ph .tabs button span{color:var(--faint);margin-left:4px}
.doc{display:block;width:100%;text-align:left;border:0;border-bottom:1px solid var(--line);border-radius:0;padding:8px 12px;cursor:pointer}
.doc:hover{background:var(--sel)}.doc.on{background:var(--sel);box-shadow:inset 3px 0 0 var(--accent)}.doc .n{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:500}
.doc .s{display:flex;justify-content:space-between;gap:6px;color:var(--muted);font-size:11.5px;margin-top:2px}
.strip{display:inline-grid;grid-auto-flow:column;gap:2px}.strip i{width:11px;height:11px;border-radius:2px;background:var(--line)}
.strip i.high{background:var(--high)}.strip i.medium{background:var(--medium)}.strip i.low{background:var(--low)}
.strip i.none{background:repeating-linear-gradient(135deg,var(--line) 0 2px,transparent 2px 4px)}
.row{display:grid;grid-template-columns:18px 80px minmax(160px,1fr) 62px 86px 42px 58px 130px;gap:10px;align-items:center;padding:7px 12px;border-bottom:1px solid var(--line);cursor:pointer;min-height:44px}
.row:hover{background:var(--sel)}.row.on{background:var(--sel);box-shadow:inset 3px 0 0 var(--accent)}.row .p{font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row .p small{display:block;font-weight:400;color:var(--muted);font-size:11.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.row .r{text-align:right}.row .d{color:var(--muted);font-size:11.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gl{font-family:var(--mono);color:var(--accent);text-align:center}.gl.reject{color:var(--low)}.gl.hold{color:var(--medium)}
.empty{padding:28px 14px;color:var(--muted)}
.dh{padding:12px 16px 10px;border-bottom:1px solid var(--line);background:inherit}.dh h2{margin:0;font-size:16px;font-weight:600}.dh .l{color:var(--muted);font-size:12px;margin-top:2px}
.dh .bar{display:flex;align-items:center;gap:10px;margin-top:10px;flex-wrap:wrap}.dh .bar .seg button kbd{font:inherit;font-size:10px;opacity:.7;margin-left:6px;border:1px solid currentColor;border-radius:2px;padding:0 3px}
.ov{display:inline-flex;align-items:center;gap:8px;font-size:12px;color:var(--muted)}.ov i{display:inline-block;width:80px;height:6px;background:var(--line);border-radius:2px;overflow:hidden}.ov i b{display:block;height:100%}
.ov i.high b{background:var(--high)}.ov i.medium b{background:var(--medium)}.ov i.low b{background:var(--low)}
.sec{padding:10px 16px 4px}.sec h3{margin:0 0 6px;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:600}
table.f{width:100%;border-collapse:collapse;table-layout:fixed}table.f td{padding:5px 6px 2px;vertical-align:top;font-size:12.5px;overflow-wrap:anywhere}
table.f td:first-child{color:var(--muted);width:118px}table.f td:nth-child(3){width:112px;text-align:right;white-space:nowrap}table.f td.v{font-weight:500}
table.f tr.x td{padding:0 6px 6px;border-bottom:1px solid var(--line);color:var(--muted);font-size:12px}table.f tr.x code{color:var(--fg)}
.bar8{display:inline-block;width:54px;height:6px;background:var(--line);border-radius:2px;vertical-align:middle;margin-right:6px;overflow:hidden}.bar8 b{display:block;height:100%}
.bar8.high b{background:var(--high)}.bar8.medium b{background:var(--medium)}.bar8.low b{background:var(--low)}
code{font-family:var(--mono);font-size:11.5px;background:var(--code);padding:1px 4px;border-radius:2px}
ul.t{margin:0;padding-left:16px}ul.t li{margin:3px 0}
.chip{display:inline-block;margin:0 6px 4px 0;padding:1px 7px;border:1px solid var(--line);border-radius:2px;font-family:var(--mono);font-size:11px;color:var(--muted)}
.chip.high{border-color:var(--low);color:var(--low)}.chip.warning{border-color:var(--medium);color:var(--medium)}
.cmp{padding:10px 12px;border-bottom:1px solid var(--line)}.cmp h4{margin:0 0 6px;font-size:13.5px;font-weight:600}.cmp h4 span{color:var(--muted);font-weight:400}
.cmp table{border-collapse:collapse;width:100%}.cmp th{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);text-align:left;padding:3px 6px;border-bottom:1px solid var(--line)}
.cmp td{padding:4px 6px;border-bottom:1px solid var(--line);font-size:12.5px}.cmp td.r,.cmp th.r{text-align:right}.cmp .note{margin-top:6px;font-size:12px;color:var(--muted)}.cmp .note.ok{color:var(--fg)}
.ta{width:100%;height:120px;font-family:var(--mono);font-size:11.5px;margin:8px 0 0}
@media (max-width:1100px){.panes{grid-template-columns:1fr;grid-auto-rows:minmax(0,auto)}.pane{border-right:0;border-bottom:1px solid var(--line);max-height:60vh}.pane:first-child{max-height:30vh}.row{grid-template-columns:18px 80px 1fr 86px}.row .pk,.row .cu,.row .ba,.row .d{display:none}.dist{display:none}}
"""

SCRIPT = r"""
(function(){
const D=window.__DATA__,R=D.records,byId=Object.fromEntries(R.map(r=>[r.record_id,r]));
const KEY='docintel-decisions-'+(D.run.started||'run');let dec={};try{dec=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
const S={filter:'review',q:'',doc:null,tab:'records',sel:null,sort:'confidence'};
const $=s=>document.querySelector(s),esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const tier=s=>s>=0.85?'high':s>=0.6?'medium':'low';
const money=v=>v==null||v===''?'':(typeof v==='number'?v.toLocaleString('en-GB',{maximumFractionDigits:v<1?4:v<100?3:2}):esc(v));
const grp=r=>(r.status==='failed'||r.status==='no_lines')?'failed':(r.needs_review?'review':'clean');
const docOf=r=>r.parent_document||r.source_document;
function strip(r){const c=r.confidence||{};return'<span class="strip" title="'+D.strip_fields.map(f=>f+' '+(c[f]?c[f].score.toFixed(2):'n/a')).join(', ')+'">'+D.strip_fields.map(f=>{const v=r[f];const x=c[f];const k=v==null?'none':(x?x.tier:'none');return'<i class="'+k+'"></i>'}).join('')+'</span>'}
function glyph(id){const d=dec[id];return d==='approve'?'<span class="gl">&#9679;</span>':d==='hold'?'<span class="gl hold">&#9684;</span>':d==='reject'?'<span class="gl reject">&times;</span>':'<span class="gl faint">&middot;</span>'}
function visible(){const q=S.q.toLowerCase();let rows=R.filter(r=>(S.filter==='all'||grp(r)===S.filter)&&(!S.doc||docOf(r)===S.doc)&&(!q||[r.source_document,r.supplier_name,r.product_name,r.inn,r.quotation_ref,r.currency].join(' ').toLowerCase().includes(q)));
 if(S.sort==='confidence')rows.sort((a,b)=>a.overall_confidence-b.overall_confidence||docOf(a).localeCompare(docOf(b))||(a.line_no||0)-(b.line_no||0));
 else if(S.sort==='document')rows.sort((a,b)=>docOf(a).localeCompare(docOf(b))||(a.line_no||0)-(b.line_no||0));
 else if(S.sort==='price')rows.sort((a,b)=>(b.price_per_uom||0)-(a.price_per_uom||0));
 else rows.sort((a,b)=>(a.supplier_name||'').localeCompare(b.supplier_name||'')||(a.line_no||0)-(b.line_no||0));return rows}
function counts(){const c={all:R.length,review:0,clean:0,failed:0};R.forEach(r=>c[grp(r)]++);return c}
function renderTop(){const need=R.filter(r=>grp(r)==='review');const done=need.filter(r=>dec[r.record_id]).length;
 $('#prog').innerHTML=`${done} of ${need.length} decided <i><b style="width:${need.length?Math.round(done/need.length*100):0}%"></b></i>`;
 const c=counts();$('#seg').innerHTML=[['review','Needs review'],['clean','Clean'],['failed','Failed'],['all','All']].map(([k,l])=>`<button class="${S.filter===k?'on':''}" data-f="${k}">${l}<span>${c[k]}</span></button>`).join('');
 document.querySelectorAll('#seg button').forEach(b=>b.onclick=()=>{S.filter=b.dataset.f;S.sel=null;render()});
 const t={high:0,medium:0,low:0};R.forEach(r=>{const x=(r.confidence||{}).price_per_uom;if(r.price_per_uom==null)t.low++;else if(x)t[x.tier]++});const n=R.length||1;
 $('#dist').innerHTML=`unit price confidence <i><b style="width:${t.high/n*100}%;background:var(--high)"></b><b style="width:${t.medium/n*100}%;background:var(--medium)"></b><b style="width:${t.low/n*100}%;background:var(--low)"></b></i><span class="k"><em><span class="dot high"></span>${t.high} high</em><em><span class="dot medium"></span>${t.medium} medium</em><em><span class="dot low"></span>${t.low} low</em></span>`}
function renderDocs(){const docs={};R.forEach(r=>{const k=docOf(r);const d=docs[k]||(docs[k]={name:k,kind:r.source_kind,supplier:r.supplier_name,n:0,rev:0,failed:false});d.n++;if(grp(r)==='review')d.rev++;if(grp(r)==='failed')d.failed=true});
 const list=Object.values(docs).sort((a,b)=>b.rev-a.rev||a.name.localeCompare(b.name));
 $('#docs').innerHTML=`<button class="doc ${S.doc?'':'on'}" data-d=""><span class="n">All documents</span><span class="s"><span>${list.length} files</span><span>${R.length} records</span></span></button>`+list.map(d=>`<button class="doc ${S.doc===d.name?'on':''}" data-d="${esc(d.name)}" title="${esc(d.name)}"><span class="n">${esc(d.name)}</span><span class="s"><span>${esc(d.kind)}${d.supplier?' &middot; '+esc(d.supplier):''}</span></span><span class="s"><span>${d.failed?'failed to load':d.n+' records'}</span><span>${d.rev?d.rev+' to review':'clean'}</span></span></button>`).join('');
 document.querySelectorAll('#docs .doc').forEach(b=>b.onclick=()=>{S.doc=b.dataset.d||null;S.sel=null;render()})}
function renderList(){const rows=visible();$('#tabs').innerHTML=[['records','Records',rows.length],['conflicts','Conflicts',(D.conflicts||[]).length],['duplicates','Duplicates',(D.duplicates||[]).length]].map(([k,l,n])=>`<button class="${S.tab===k?'on':''}" data-t="${k}">${l}<span>${n}</span></button>`).join('');
 document.querySelectorAll('#tabs button').forEach(b=>b.onclick=()=>{S.tab=b.dataset.t;render()});
 const el=$('#list');
 if(S.tab==='conflicts'){const cs=D.conflicts||[];el.innerHTML=cs.length?cs.map(c=>`<div class="cmp"><h4>${esc(c.inn_normalised)} ${esc(c.strength||'')} <span>${esc(c.form||'')}</span></h4><table><thead><tr><th>Supplier</th><th>Currency</th><th class="r">Pack</th><th class="r">Unit price</th></tr></thead><tbody>${c.suppliers.map((s,i)=>`<tr><td>${esc(s)}</td><td class="mono">${esc(c.currencies[i])}</td><td class="r num">${money(c.units_per_pack[i])} ${esc(c.uoms[i])}</td><td class="r num mono">${money(c.unit_prices[i])}</td></tr>`).join('')}</tbody></table><div class="note ${c.comparable?'ok':''}">${esc(c.note)}</div></div>`).join(''):'<div class="empty">No product was quoted by more than one supplier.</div>';return}
 if(S.tab==='duplicates'){const ds=D.duplicates||[];el.innerHTML=ds.length?ds.map(d=>`<div class="cmp"><h4>${esc(d.supplier||'')} <span>${esc(d.quotation_ref)}</span></h4><div class="sm">${d.documents.map(esc).join('<br>')}</div><div class="note">${d.matched_lines} matched lines &middot; ${d.agreements} agreeing values &middot; ${d.disagreements.length} disagreements</div>${d.disagreements.length?`<table><thead><tr><th>Field</th><th>Product</th><th>Values</th></tr></thead><tbody>${d.disagreements.map(x=>`<tr><td class="mono">${esc(x.field)}</td><td>${esc(x.product||'')}</td><td class="mono">${esc(Object.entries(x).filter(([k])=>!['field','product'].includes(k)).map(([k,v])=>k+': '+v).join(' vs '))}</td></tr>`).join('')}</tbody></table>`:''}</div>`).join(''):'<div class="empty">No quotation arrived as more than one file.</div>';return}
 if(!rows.length){el.innerHTML='<div class="empty">Nothing matches this filter.</div>';return}
 if(S.sel==null||!rows.some(r=>r.record_id===S.sel))S.sel=rows[0].record_id;
 el.innerHTML=rows.map(r=>`<div class="row ${S.sel===r.record_id?'on':''}" tabindex="0" data-id="${esc(r.record_id)}">${glyph(r.record_id)}${strip(r)}<div class="p">${esc(r.product_name||(r.status==='failed'?'could not load':'(no product name)'))}<small>${esc(r.inn||'')} ${esc(r.strength||'')}</small></div><div class="pk num sm">${r.units_per_pack!=null?money(r.units_per_pack)+' '+esc(r.uom||''):esc(r.uom||'')}</div><div class="r num mono">${money(r.price_per_uom)}</div><div class="cu mono sm">${esc(r.currency||'')}</div><div class="ba sm muted">${esc(r.price_basis||'')}</div><div class="d" title="${esc(docOf(r))}">${esc(docOf(r))}</div></div>`).join('');
 document.querySelectorAll('.row').forEach(x=>{x.onclick=()=>{S.sel=x.dataset.id;render()}});
 const on=el.querySelector('.row.on');if(on)on.scrollIntoView({block:'nearest'})}
function fieldRow(r,f){const c=(r.confidence||{})[f],ev=(r.evidence||{})[f],v=r[f];
 if(v==null){const why=c&&c.reasons&&c.reasons[0]||'not stated';const ill=/could not read/.test(why);return`<tr><td>${f}</td><td class="muted">${ill?'illegible':'not stated'}</td><td class="sm">${ill?'<span class="chip high">unreadable</span>':''}</td></tr><tr class="x"><td></td><td colspan="2">${ill?esc(why):''}</td></tr>`}
 const t=c?c.tier:'';return`<tr><td>${f}</td><td class="v num">${typeof v==='number'?money(v):esc(v)}</td><td class="num sm"><span class="bar8 ${t}"><b style="width:${c?Math.round(c.score*100):0}%"></b></span>${c?c.score.toFixed(2):''}</td></tr><tr class="x"><td></td><td colspan="2">${c?esc((c.reasons||[]).join('; ')):''}${ev?` <code>${esc(ev)}</code>`:''}</td></tr>`}
function renderDetail(){const el=$('#detail');const r=byId[S.sel];if(!r){el.innerHTML='<div class="empty">Select a record.</div>';return}
 const t=tier(r.overall_confidence),d=dec[r.record_id]||'';const conflicts=(D.conflicts||[]).filter(c=>c.record_ids.includes(r.record_id));
 el.innerHTML=`<div class="dh"><h2>${esc(r.product_name||(r.status==='failed'?'Could not load this file':'(no product name)'))}</h2>
 <div class="l">${esc(r.supplier_name||'')}${r.quotation_ref?' &middot; '+esc(r.quotation_ref):''}</div>
 <div class="l">${esc(docOf(r))}${r.parent_document?' &rarr; '+esc(r.source_document):''} &middot; ${esc(r.source_locator||'')} &middot; <span class="mono">${esc(r.record_id)}</span></div>
 <div class="bar"><span class="seg"><button class="${d==='approve'?'on':''}" data-d="approve">Approve<kbd>A</kbd></button><button class="${d==='hold'?'on':''}" data-d="hold">Hold<kbd>H</kbd></button><button class="${d==='reject'?'on':''}" data-d="reject">Reject<kbd>R</kbd></button></span>
 <span class="ov">overall <i class="${t}"><b style="width:${Math.round(r.overall_confidence*100)}%"></b></i>${r.overall_confidence.toFixed(2)}</span></div></div>
 ${(r.review_reasons||[]).length?`<div class="sec"><h3>Why it needs a person</h3><ul class="t">${r.review_reasons.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`:`<div class="sec"><h3>Review</h3><div class="muted sm">Nothing flagged. Every key field is grounded in the source.</div></div>`}
 <div class="sec"><h3>Fields</h3><table class="f"><tbody>${D.field_order.filter(f=>f in r).map(f=>fieldRow(r,f)).join('')}</tbody></table></div>
 ${r.superseded?`<div class="sec"><h3>Corrected in the document</h3><div class="sm"><span class="mono">${esc(r.superseded.field)}</span>: ${money(r.superseded.old)} &rarr; <b>${money(r.superseded.new)}</b></div><div class="sm muted">${esc(r.superseded.reason||'')}</div></div>`:''}
 ${r.price_tiers?`<div class="sec"><h3>Volume tiers</h3><table class="f"><tbody>${r.price_tiers.map(x=>`<tr><td>${money(x.min_packs)}${x.max_packs!=null?' to '+money(x.max_packs):' or more'} packs</td><td class="v num mono">${money(x.price_per_pack)}</td></tr>`).join('')}</tbody></table></div>`:''}
 ${(r.flags||[]).length?`<div class="sec"><h3>Flags</h3>${r.flags.map(f=>`<span class="chip ${esc(f.severity)}" title="${esc(f.detail)}">${esc(f.code)}</span>`).join('')}</div>`:''}
 ${(r.notes||[]).length?`<div class="sec"><h3>Notes</h3><ul class="t sm">${r.notes.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`:''}
 ${conflicts.length?`<div class="sec"><h3>Also quoted by</h3>${conflicts.map(c=>`<div class="sm">${esc(c.suppliers.filter(s=>s!==r.supplier_name).join(', '))} <span class="muted">&middot; ${esc(c.note)}</span></div>`).join('')}</div>`:''}
 <div class="sec"><h3>Source</h3><div class="sm mono muted">${esc(r.source_path||r.source_document)}</div></div>`;
 document.querySelectorAll('.dh .seg button').forEach(b=>b.onclick=()=>decide(r.record_id,b.dataset.d))}
function decide(id,d){if(dec[id]===d)delete dec[id];else dec[id]=d;try{localStorage.setItem(KEY,JSON.stringify(dec))}catch(e){}render()}
function render(){renderTop();renderDocs();renderList();renderDetail()}
document.addEventListener('keydown',e=>{if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA'||e.target.tagName==='SELECT')return;const rows=visible();const i=rows.findIndex(r=>r.record_id===S.sel);
 if(e.key==='j'||e.key==='ArrowDown'){if(i<rows.length-1){S.sel=rows[i+1].record_id;render()}e.preventDefault()}
 else if(e.key==='k'||e.key==='ArrowUp'){if(i>0){S.sel=rows[i-1].record_id;render()}e.preventDefault()}
 else if(S.sel&&(e.key==='a'||e.key==='h'||e.key==='r')){decide(S.sel,{a:'approve',h:'hold',r:'reject'}[e.key])}});
$('#q').oninput=e=>{S.q=e.target.value;renderList();renderDetail()};$('#sort').onchange=e=>{S.sort=e.target.value;renderList();renderDetail()};
$('#copy').onclick=()=>{const payload=JSON.stringify({run:D.run.started,decisions:dec},null,2);const ok=()=>{$('#copy').textContent='Copied';setTimeout(()=>$('#copy').textContent='Copy decisions',1500)};
 const show=()=>{$('#out').hidden=false;$('#out').value=payload};
 if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(payload).then(ok).catch(show);else show()};
$('#clear').onclick=()=>{dec={};try{localStorage.removeItem(KEY)}catch(e){}render()};
render();
})();
"""


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
        "field_order": list(FIELD_ORDER),
        "key_fields": list(KEY_FIELDS),
        "strip_fields": list(STRIP_FIELDS),
    }
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    meta = " &middot; ".join(
        x
        for x in (
            f"{run.get('documents', '?')} documents",
            f"{len(records)} records",
            f"extractor {run.get('extractor', '?')}",
            f"model {run['model']}" if run.get("model") else "",
            f"as of {run['as_of']}" if run.get("as_of") else "",
            str(run.get("started", "")),
        )
        if x
    )
    body = f"""<title>Quotation Review</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{STYLE}</style>
<div class="app">
<header class="top"><span class="brand"><b>docintel</b> &middot; Quotation review</span><span class="meta">{meta}</span><span id="prog" class="progress"></span></header>
<div class="tools"><span id="seg" class="seg"></span><input id="q" type="search" placeholder="Search" size="26"><select id="sort"><option value="confidence">Lowest confidence first</option><option value="document">By document</option><option value="supplier">By supplier</option><option value="price">Highest unit price</option></select><button id="copy">Copy decisions</button><button id="clear" class="sm">Clear</button><span id="dist" class="dist"></span></div>
<textarea id="out" class="ta" hidden></textarea>
<div class="panes">
<aside class="pane"><div class="ph">Documents</div><div id="docs"></div></aside>
<section class="pane"><div class="ph"><span id="tabs" class="tabs"></span></div><div id="list"></div></section>
<section class="pane"><div id="detail"></div></section>
</div></div>
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
