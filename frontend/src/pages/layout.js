import {state} from '../stores/session.js';
import {esc} from '../utils/html.js';
import {badge} from '../components/common/status.js';
import {field,select} from '../components/common/fields.js';
import {DIMENSIONS} from '../constants/enums.js';
import {api,post} from '../api/client.js';
import {values} from '../hooks/form.js';
export function render(){
 return `<div class="split"><section class="panel">
 <h2>把复核问题变成行列维度</h2>
 <p class="notice">透视按提交时的场次渠道快照冻结，并记录每个场次的版本指纹。场次修订或拆分确认后需新建方案，不覆盖已导出的结算证据。</p>
 ${state.pivots.map(r=>`<button class="study" data-pivot="${r.id}">#${r.id} ${esc(r.name)} ${badge(r.state)} · ${esc(r.row_dim)} × ${esc(r.col_dim)}</button>`).join('')||'<p>尚无方案。先尝试“场馆 × 渠道”，核对每个渠道的净结算。</p>'}
 </section><aside class="side"><h2>新建透视方案</h2><form id="pivot">
 ${field('方案名','name','text','required value="11月场馆渠道结算复核"')}
 ${select('行维度','row_dim',DIMENSIONS)}
 ${select('列维度','col_dim',[DIMENSIONS[2],DIMENSIONS[0],DIMENSIONS[1],DIMENSIONS[3]])}
 <p>白名单维度：场馆、演出、渠道、月份。行列不能相同。金额按渠道求和；场次数与座位按场次去重；上座率=总核验/去重总座位。</p>
 <button class="primary">提交后台透视</button></form></aside></div>`;
}
export function bind(ctx){
 const {run,rerender}=ctx;
 const f=document.querySelector('#pivot');
 if(f)f.onsubmit=e=>{e.preventDefault();run(async()=>{
  const created=await post('/pivots',values(f));
  state.selected=created;state.drill=null;state.chosen=null;
  await ctx.reload();
  if(location.hash!=='#2')location.hash='2';else rerender();
 })};
}
