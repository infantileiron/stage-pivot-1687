import {state} from '../stores/session.js';
import {esc} from '../utils/html.js';
import {badge} from '../components/common/status.js';
import {field} from '../components/common/fields.js';
import {money} from '../utils/format.js';
import {api,post} from '../api/client.js';
import {values} from '../hooks/form.js';
export function render(){
 const c=state.chosen,e=state.selected;
 return `<div class="split"><section class="panel">
 <h2>账面与回单，保留解释</h2>
 <p class="notice">差异=回单预期净额−冻结账面净额。签核表示财务已核对原因，不自动修改结算数据或触发付款。历史复核单在渠道拆分与迁移后仍可读取。</p>
 ${state.reviews.map(r=>`<article class="rec"><h3>#${r.id} ${esc(r.row_key)} × ${esc(r.col_key)} ${badge(r.status)}</h3>
  <p>透视 #${r.pivot_id} · 账面 ${money(r.book_cents)} / 回单 ${money(r.expected_cents)} / 差异 <b>${money(r.difference_cents)} 元</b></p>
  <p>${esc(r.note)}</p>
  ${state.user.role==='admin'&&r.status==='draft'?`<button data-approve="${r.id}">财务负责人签核</button>`:''}</article>`).join('')
  ||'<p>暂无复核单。先在透视结果下钻单元格，再起草差异复核。</p>'}
 </section><aside class="side"><h2>起草差异复核</h2>
 ${c&&e?`<p>透视 #${e.id}<br>${esc(c.row_key)} × ${esc(c.col_key)}<br>账面净额 ${money(c.net_cents)} 元<br>核验 ${c.checked}/${c.seats}</p>
 <form id="review"><input type="hidden" name="pivot_id" value="${e.id}">
  <input type="hidden" name="row_key" value="${esc(c.row_key)}">
  <input type="hidden" name="col_key" value="${esc(c.col_key)}">
  ${field('回单预期净额 / 分','expected_cents','number',`required min=0 value=${c.net_cents}`)}
  <label>差异原因与核对证据<textarea name="note" minlength="8" required rows="6"></textarea></label>
  <button class="primary">保存待签核复核</button></form>`
 :'<p>请先到结算透视页下钻，再选择“为该单元起草差异复核”。</p>'}
 </aside></div>`;
}
export function bind(ctx){
 const {run,rerender,notify}=ctx;
 const f=document.querySelector('#review');
 if(f)f.onsubmit=ev=>{ev.preventDefault();run(async()=>{
  const d=values(f);
  await post('/reviews',{pivot_id:Number(d.pivot_id),row_key:d.row_key,col_key:d.col_key,
   expected_cents:Number(d.expected_cents),note:d.note});
  notify('复核草案已保存');state.chosen=null;await ctx.reload();rerender();
 })};
 document.querySelectorAll('[data-approve]').forEach(b=>b.onclick=()=>run(async()=>{
  await post('/reviews/'+b.dataset.approve+'/approve',{});await ctx.reload();rerender();
 }));
}
