import {state} from '../stores/session.js';
import {esc} from '../utils/html.js';
import {badge} from '../components/common/status.js';
import {money,pct} from '../utils/format.js';
import {api,post} from '../api/client.js';
export function render(){
 const e=state.selected,r=e?.result;
 const drill=state.drill,filter=(state.drillFilter||'').toLowerCase();
 const rows=drill?drill.rows.filter(x=>!filter||JSON.stringify(x).toLowerCase().includes(filter)):[];
 return `<section class="panel">
 <div class="result-head"><h2>${e?esc(e.name):'选择一份透视方案'} ${e?badge(e.state):''}</h2>
 <span class="actions"><button id="refresh">刷新状态</button>${e?.state==='done'?`<button id="download">下载透视与明细 JSON</button><button id="download-csv">下载逆透明明细 CSV</button>`:''}</span></div>
 ${e?.state==='done'?`<div class="metrics">
  <div><strong>${money(r.total.net_cents)}</strong>净结算 / 元</div>
  <div><strong>${pct(r.total.occupancy)}</strong>加权上座率</div>
  <div><strong>${r.total.count}</strong>冻结场次（去重）</div>
  <div><strong>${r.total.seats}</strong>场次座位（去重）</div>
  <div><strong>${r.total.checked}</strong>核验人数（按渠道合计）</div>
  <div><strong>${r.conserved?'一致':'异常'}</strong>行列总计守恒</div></div>
 <p class="notice">金额按渠道相加；场次数与座位按场次编号去重，跨渠道的行、列与总计由原始渠道明细重新计算。核验按渠道相加且每场合计不超过座位。单元格展示净结算 / 元；点击有记录的单元格下钻冻结明细。</p>
 <p class="muted">版本指纹 <code>${esc((r.version_checksum||'').slice(0,16)||'旧版快照')}</code> · 快照校验 <code>${esc((r.checksum||'').slice(0,16))}</code></p>
 <div class="scroll"><table class="pivot"><thead><tr><th>${esc(e.row_dim)} / ${esc(e.col_dim)}</th>
 ${r.col_keys.map(b=>`<th>${esc(b)}</th>`).join('')}<th>行合计</th></tr></thead><tbody>
 ${r.row_keys.map(a=>`<tr><th>${esc(a)}</th>${r.col_keys.map(b=>{
  const c=r.cells.find(c=>c.row_key===a&&c.col_key===b);
  return `<td>${c&&c.count?`<button data-drill-row="${esc(a)}" data-drill-col="${esc(b)}">${money(c.net_cents)}</button><small>${c.count}场 · ${c.seats}座 · ${pct(c.occupancy)}</small>`:'—'}</td>`;
 }).join('')}<td>${money(r.row_totals.find(c=>c.key===a).net_cents)}<small>${r.row_totals.find(c=>c.key===a).count}场 · ${r.row_totals.find(c=>c.key===a).seats}座</small></td></tr>`).join('')}
 <tr class="total"><th>列合计</th>${r.col_totals.map(c=>`<td>${money(c.net_cents)}<small>${c.count}场 · ${c.seats}座</small></td>`).join('')}
 <td>${money(r.total.net_cents)}<small>${r.total.count}场 · ${r.total.seats}座</small></td></tr></tbody></table></div>
 ${drill?`<div class="drill">
 <h3>冻结下钻：${esc(drill.cell.row_key)} × ${esc(drill.cell.col_key)}</h3>
 <p>净结算 ${money(drill.cell.net_cents)} 元；核验 ${drill.cell.checked}/${drill.cell.seats}；加权上座率 ${pct(drill.cell.occupancy)}；场次 ${drill.cell.count}</p>
 <input id="drill-filter" placeholder="筛选场次 / 渠道 / 演出" value="${esc(state.drillFilter||'')}">
 <div class="scroll"><table><thead><tr><th>场次</th><th>版本</th><th>日期</th><th>场馆 / 演出</th><th>渠道</th><th>票款 ¥</th><th>退款 ¥</th><th>渠道费 ¥</th><th>净额 ¥</th><th>核验/座位</th></tr></thead><tbody>
 ${rows.map(x=>`<tr><td>${esc(x.code)}</td><td>v${x.performance_version??1}</td><td>${esc(x.day)}</td>
  <td>${esc(x.venue)}<small class="muted">${esc(x.play)}</small></td><td>${esc(x.channel)}</td>
  <td>${money(x.gross_cents)}</td><td>${money(x.refund_cents)}</td><td>${money(x.fee_cents)}</td>
  <td>${money(x.gross_cents-x.refund_cents-x.fee_cents)}</td><td>${x.checked}/${x.seats}</td></tr>`).join('')||'<tr><td colspan="10">没有匹配的渠道明细。</td></tr>'}
 </tbody></table></div>
 <button id="draft-review">为该单元起草差异复核</button></div>`:''}
 <p class="notice">${esc(r.method)}</p>`
 :e?`<p class="notice">${esc(e.error||'后台计算中，请稍后刷新。')}</p>`:'<p class="notice">到透视布局页创建方案，或选择下方历史记录。</p>'}
 <h3>历史透视</h3>
 ${state.pivots.map(p=>`<button class="study" data-pivot="${p.id}">#${p.id} ${esc(p.name)} · ${esc(p.state)}</button>`).join('')}</section>`;
}
function csv(rows){
 const head=['code','performance_version','day','venue','play','channel','gross_cents','refund_cents','fee_cents','net_cents','seats','checked'];
 const q=v=>`"${String(v??'').replace(/"/g,'""')}"`;
 return [head.join(','),...rows.map(r=>head.map(k=>k==='net_cents'?r.gross_cents-r.refund_cents-r.fee_cents:r[k]).map(q).join(','))].join('\n');
}
export function bind(ctx){
 const {run,rerender,reload,download}=ctx;
 document.querySelectorAll('[data-pivot]').forEach(b=>b.onclick=()=>run(async()=>{
  state.selected=await api('/pivots/'+b.dataset.pivot);state.drill=null;state.chosen=null;
  if(location.hash!=='#2')location.hash='2';else rerender();
 }));
 document.querySelectorAll('[data-drill-row]').forEach(b=>b.onclick=()=>run(async()=>{
  const cur=state.selected;
  state.drill=await api('/pivots/'+cur.id+'/drill?'+new URLSearchParams({row_key:b.dataset.drillRow,col_key:b.dataset.drillCol}));
  state.drillFilter='';
  rerender();document.querySelector('.drill')?.scrollIntoView({block:'center'});
 }));
 const filter=document.querySelector('#drill-filter');
 if(filter){filter.oninput=()=>{state.drillFilter=filter.value;rerender();document.querySelector('#drill-filter')?.focus()}}
 document.querySelector('#draft-review')?.addEventListener('click',()=>{state.chosen=state.drill.cell;location.hash='3'});
 document.querySelector('#refresh')?.addEventListener('click',()=>run(async()=>{
  await reload();state.selected=await api('/pivots/'+state.selected.id);rerender();
 }));
 document.querySelector('#download')?.addEventListener('click',()=>run(async()=>{
  download('stage-pivot-'+state.selected.id+'.json',await api('/pivots/'+state.selected.id+'/export'));
 }));
 document.querySelector('#download-csv')?.addEventListener('click',()=>{
  const rows=state.selected?.result?.snapshot||[];
  const u=URL.createObjectURL(new Blob([csv(rows)],{type:'text/csv;charset=utf-8'}));
  const a=document.createElement('a');a.href=u;a.download='stage-pivot-'+state.selected.id+'.csv';a.click();URL.revokeObjectURL(u);
 });
}
