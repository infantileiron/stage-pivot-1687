import {state} from '../stores/session.js';
import {esc} from '../utils/html.js';
import {badge} from '../components/common/status.js';
import {field,select} from '../components/common/fields.js';
import {VENUES,CHANNELS} from '../constants/enums.js';
import {money} from '../utils/format.js';
import {channelEditor,readChannels,channelTable} from '../components/channels.js';
import {values} from '../hooks/form.js';
import {api,post} from '../api/client.js';
const blank=()=>({day:'2026-11-15',venue:VENUES[0],play:'',seats:100,
 channels:[{channel:'剧院直营',gross_cents:0,refund_cents:0,fee_cents:0,checked:0}]});
const fmtTime=t=>t?esc(t.replace('T',' ').slice(0,19)):'—';
function perfRow(p){
 return `<tr class="${state.expanded===p.id?'chosen':''}">
 <td><button class="link" data-expand="${p.id}">${esc(p.code)}</button></td>
 <td>${esc(p.day)}</td>
 <td>${esc(p.venue)}<small class="muted">${esc(p.play)}</small></td>
 <td>${p.seats}</td><td>${p.channel_count}</td>
 <td>${p.checked_total}/${p.seats}</td>
 <td>${money(p.net_cents)}</td><td>v${p.version}</td></tr>`;
}
function detail(p){
 const revs=state.revisions||[];const drafts=(state.splits||[]).filter(d=>d.performance_id===p.id);
 return `<tr class="detail-row"><td colspan="8"><div class="detail">
 <div class="detail-head"><h3>${esc(p.code)} · ${esc(p.venue)} / ${esc(p.play)}</h3>
  <span class="tag">座位 ${p.seats} · 核验 ${p.checked_total} · 版本 v${p.version}</span>
  <span class="actions"><button data-edit-perf="${p.id}">修订场次</button>
  <button data-new-split="${p.id}">起草拆分</button>
  <button data-export-perf="${p.id}">下载该场 JSON</button></span></div>
 ${channelTable(p.channels)}
 <p class="notice">座位为场次共用：各渠道核验合计 ${p.checked_total} 不得超过 ${p.seats}。透视中金额按渠道相加，场次数与座位按场次去重。</p>
 <h4>拆分草稿</h4>
 ${drafts.length?drafts.map(d=>`<div class="draft ${d.status}">
  <div class="detail-head"><b>草稿 #${d.id}</b> ${badge(d.status)}
   <span class="muted">基准 v${d.base_version}${d.stale?' · 已过期':''} · 更新 ${fmtTime(d.updated)}</span>
   <span class="actions">${d.status==='draft'
    ?`<button data-edit-split="${d.id}">继续编辑</button><button class="primary" data-confirm-split="${d.id}">确认整场替换</button>`
    :`<span class="muted">已应用为 v${d.applied_version}</span>`}</span></div>
  ${d.status==='draft'&&d.stale?'<p class="error">场次已产生新版本，确认会被拒绝，请重新起草。</p>':''}
  ${channelTable(d.channels)}
  ${d.note?`<p class="muted">说明：${esc(d.note)}</p>`:''}
  ${d.result?`<p class="muted">确认结果：v${d.result.before_version} → v${d.result.after_version}，前后版本整场可追溯；重复确认不重复入账。</p>`:''}
 </div>`).join(''):'<p class="muted">尚无拆分草稿。拆分从草稿开始，确认后整场原子替换。</p>'}
 <h4>历史版本</h4>
 ${revs.length?`<div class="scroll"><table><thead><tr><th>版本</th><th>动作</th><th>渠道</th><th>座位</th><th>时间</th><th></th></tr></thead><tbody>
 ${revs.map(r=>`<tr><td>v${r.version}</td><td>${esc(r.action)}</td><td>${r.snapshot.channel_count}</td><td>${r.snapshot.seats}</td>
 <td><small>${fmtTime(r.created)}</small></td>
 <td>${r.version!==p.version?`<button data-restore="${r.id}" data-version="${p.version}" data-perf="${p.id}">恢复为 v${r.version}</button>`:''}</td></tr>`).join('')}
 </tbody></table></div>`:'<p class="muted">暂无历史版本。</p>'}
 </div></td></tr>`;
}
 export function render(){
 const editing=state.editingPerf;
 const form=editing||blank();
 const seatLimit=editing?editing.seats:form.seats;
 return `<div class="split"><section class="panel">
 <div class="result-head"><h2>场次票款，按渠道留据</h2><button data-export-all>下载全部场次与渠道 JSON</button></div>
 <p>每个场次共用日期、场馆、演出与座位；各渠道独立记录票款、退款、渠道费与核验人数。同场渠道唯一，核验合计不得超过座位。</p>
 <div class="scroll"><table><thead><tr><th>场次</th><th>日期</th><th>场馆 / 演出</th><th>座位</th><th>渠道</th><th>核验/座位</th><th>净结算 ¥</th><th>版本</th></tr></thead><tbody>
 ${state.perfs.map(perfRow).join('')||'<tr><td colspan="8">暂无场次。请在右侧录入首条数据。</td></tr>'}
 </tbody></table></div>
 ${state.expanded?(()=>{const p=state.perfs.find(x=>x.id===state.expanded);return p?detail(p):''})():''}
 </section><aside class="side">
 <h2>${editing?`修订 ${esc(editing.code)}`:'录入场次'}</h2>
 <form id="perf">
 ${editing?`<input type="hidden" name="expected_version" value="${editing.version}">
  <p class="notice">当前版本 v${editing.version}。保存会生成 v${editing.version+1}；若他人先修订，服务器拒绝过期覆盖。</p>`:field('场次编号','code','text','required value="YM-181"')}
 ${field('业务日期','day','date','required value="'+form.day+'"')}
 ${select('场馆','venue',VENUES.map(x=>[x,x]))}
 ${field('演出名称','play','text','required value="'+esc(form.play)+'"')}
 ${field('座位（整场共用）','seats','number','required min=0 max=10000 step=1 value="'+form.seats+'"')}
 ${channelEditor(form.channels,{seatLimit,prefix:'ch'})}
 <button class="primary">${editing?'保存为新版本':'保存场次与渠道'}</button>
 ${editing?'<button type="button" data-cancel-edit>取消修订</button>':''}
 </form>
 <h2>拆分场次</h2>
 ${state.splitTarget?`<form id="split">
  <p class="notice">为 ${esc(state.splitTarget.code)} 起草拆分，基准版本 v${state.splitTarget.version}。草稿保存后仍可编辑，确认才整场原子替换。</p>
  <input type="hidden" name="perf_id" value="${state.splitTarget.id}">
  <input type="hidden" name="base_version" value="${state.splitTarget.version}">
  <input type="hidden" name="split_id" value="${state.splitDraft?.id??''}">
  <p>座位 ${state.splitTarget.seats}；核验合计上限即座位。</p>
  ${channelEditor(state.splitDraft?.channels??state.splitTarget.channels,{seatLimit:state.splitTarget.seats,prefix:'sp'})}
  <label>拆分说明<textarea name="note" rows="3">${esc(state.splitDraft?.note??'')}</textarea></label>
  <button class="primary">${state.splitDraft?'保存草稿修改':'保存拆分草稿'}</button>
  <button type="button" data-cancel-split>取消</button>
 </form>`:'<p class="muted">点击上方场次编号展开，再选“起草拆分”，可把同场票款拆到多个渠道。</p>'}
 </aside></div>`;
}
function setSelect(form,name,value){
 const el=form.querySelector(`[name="${name}"]`);if(el&&value!==undefined&&value!==null)el.value=value;
}
function bindChannelRows(form,prefix){
 const fieldset=form.querySelector('fieldset.channels');if(!fieldset)return;
 const seatInput=form.querySelector('[name="seats"]');
 const limitOf=()=>{
  if(seatInput&&seatInput.value!=='')return Number(seatInput.value);
  const v=fieldset.dataset.seatLimit;
  return v===''||v==null?null:Number(v);
 };
 const recalc=()=>{
  const sum=[...form.querySelectorAll(`[name^="${prefix}_checked_"]`)].reduce((a,i)=>a+Number(i.value||0),0);
  const sumEl=form.querySelector('.checked-sum');sumEl&&(sumEl.textContent=sum);
  const limit=limitOf();
  const cap=form.querySelector('.seat-cap');cap&&(cap.textContent=limit===null?'':`/ 座位 ${limit}`);
  fieldset.querySelectorAll('.error').forEach(e=>e.remove());
  if(limit!==null&&sum>limit){
   const p=document.createElement('p');p.className='error';
   p.textContent=`各渠道核验合计 ${sum} 超过座位 ${limit}，保存将被拒绝。`;
   fieldset.prepend(p);
  }
 };
 form.addEventListener('input',recalc);
 const renumber=()=>{
  [...fieldset.querySelectorAll('.channel-row')].forEach((row,i)=>{
   row.querySelector('select').name=`${prefix}_channel_${i}`;
   ['gross','refund','fee','checked'].forEach((k,j)=>{row.querySelectorAll('input')[j].name=`${prefix}_${k}_${i}`});
   const rm=row.querySelector('[data-remove-channel]');if(rm)rm.dataset.removeChannel=i;
  });
 };
 fieldset.addEventListener('click',ev=>{
  const rm=ev.target.closest('[data-remove-channel]');
  if(rm){
   if(fieldset.querySelectorAll('.channel-row').length<=1){notify('至少保留一个渠道');return}
   rm.closest('.channel-row').remove();renumber();recalc();return;
  }
  const add=ev.target.closest('[data-add-channel]');
  if(add){
   const n=fieldset.querySelectorAll('.channel-row').length;
   if(n>=3){notify('每场最多三个渠道');return}
   const wrap=document.createElement('div');wrap.className='channel-row';
   wrap.innerHTML=`<label>渠道<select name="${prefix}_channel_${n}">${CHANNELS.map(x=>`<option>${esc(x)}</option>`).join('')}</select></label>
   <label>票款 / 分<input name="${prefix}_gross_${n}" type="number" min="0" step="1" required value="0"></label>
   <label>退款 / 分<input name="${prefix}_refund_${n}" type="number" min="0" step="1" required value="0"></label>
   <label>渠道费 / 分<input name="${prefix}_fee_${n}" type="number" min="0" step="1" required value="0"></label>
   <label>核验<input name="${prefix}_checked_${n}" type="number" min="0" step="1" required value="0"></label>
   <button type="button" class="ghost" data-remove-channel="${n}">移除</button>`;
   add.before(wrap);recalc();
  }
 });
 recalc();
}
export function bind(ctx){
 const {run,rerender,download,notify}=ctx;
 document.querySelectorAll('[data-expand]').forEach(b=>b.onclick=()=>run(async()=>{
  const id=Number(b.dataset.expand);
  state.expanded=state.expanded===id?null:id;state.revisions=[];state.splitTarget=null;state.splitDraft=null;
  if(state.expanded)[state.revisions,state.splits]=await Promise.all([
   api('/performances/'+state.expanded+'/revisions'),api('/splits?performance_id='+state.expanded)]);
  rerender();
 }));
 document.querySelectorAll('[data-edit-perf]').forEach(b=>b.onclick=()=>{
  state.editingPerf=state.perfs.find(p=>p.id===Number(b.dataset.editPerf));rerender();
 });
 document.querySelector('[data-cancel-edit]')?.addEventListener('click',()=>{state.editingPerf=null;rerender()});
 document.querySelectorAll('[data-new-split]').forEach(b=>b.onclick=()=>{
  state.splitTarget=state.perfs.find(p=>p.id===Number(b.dataset.newSplit));state.splitDraft=null;rerender();
 });
 document.querySelector('[data-cancel-split]')?.addEventListener('click',()=>{state.splitTarget=null;state.splitDraft=null;rerender()});
 document.querySelectorAll('[data-edit-split]').forEach(b=>b.onclick=()=>run(async()=>{
  const d=await api('/splits/'+b.dataset.editSplit);
  state.splitDraft=d;state.splitTarget=state.perfs.find(p=>p.id===d.performance_id);rerender();
 }));
 document.querySelectorAll('[data-confirm-split]').forEach(b=>b.onclick=()=>run(async()=>{
  if(!confirm('确认后将以草稿整场原子替换该场次的渠道与座位，是否继续？'))return;
  const d=await post('/splits/'+b.dataset.confirmSplit+'/confirm',{});
  notify(d.status==='confirmed'?'拆分已确认并整场替换；重复确认不会重复入账':'状态：'+d.status);
  await ctx.reload();state.expanded=d.performance_id;state.splitDraft=d;
  [state.revisions,state.splits]=await Promise.all([
   api('/performances/'+d.performance_id+'/revisions'),api('/splits?performance_id='+d.performance_id)]);
  rerender();
 }));
 document.querySelectorAll('[data-restore]').forEach(b=>b.onclick=()=>run(async()=>{
  await post('/performances/'+b.dataset.perf+'/revisions/'+b.dataset.restore+'/restore',{expected_version:Number(b.dataset.version)});
  notify('已恢复历史版本并生成新版本');await ctx.reload();state.expanded=Number(b.dataset.perf);
  state.revisions=await api('/performances/'+b.dataset.perf+'/revisions');rerender();
 }));
 document.querySelector('[data-export-all]').onclick=()=>run(async()=>{
  download('performances-channels.json',await api('/performances/export'));
 });
 document.querySelectorAll('[data-export-perf]').forEach(b=>b.onclick=()=>run(async()=>{
  download('performance-'+b.dataset.exportPerf+'.json',await api('/performances/'+b.dataset.exportPerf+'/export'));
 }));
 const pf=document.querySelector('#perf');
 if(pf){
  const e=state.editingPerf;const form=e||blank();
  if(!e)setSelect(pf,'code','YM-181');
  setSelect(pf,'day',form.day);setSelect(pf,'venue',form.venue);setSelect(pf,'play',form.play);setSelect(pf,'seats',form.seats);
  bindChannelRows(pf,'ch');
  pf.onsubmit=ev=>{ev.preventDefault();run(async()=>{
   const base=values(pf);const channels=readChannels(pf,{prefix:'ch'});
   const body={day:base.day,venue:base.venue,play:base.play,seats:Number(base.seats),channels};
   if(e){body.code=e.code;body.expected_version=e.version;
    await api('/performances/'+e.id,{method:'PUT',body:JSON.stringify(body)});state.editingPerf=null;notify('已保存为 v'+(e.version+1));}
   else{body.code=base.code;await post('/performances',body);notify('场次已录入');}
   await ctx.reload();state.expanded=null;rerender();
  })};
 }
 const sf=document.querySelector('#split');
 if(sf){
  bindChannelRows(sf,'sp');
  sf.onsubmit=ev=>{ev.preventDefault();run(async()=>{
   const base=values(sf);const channels=readChannels(sf,{prefix:'sp'});
   if(base.split_id)await api('/splits/'+base.split_id,{method:'PUT',body:JSON.stringify({channels,note:base.note})});
   else await post('/performances/'+base.perf_id+'/splits',{base_version:Number(base.base_version),channels,note:base.note});
   notify('拆分草稿已保存，确认前不会改动场次');
   const pid=Number(base.perf_id);state.splitTarget=null;state.splitDraft=null;state.expanded=pid;
   await ctx.reload();[state.splits,state.revisions]=await Promise.all([
    api('/splits?performance_id='+pid),api('/performances/'+pid+'/revisions')]);rerender();
  })};
 }
}
