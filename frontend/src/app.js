import {api,post} from './api/client.js';
import {state} from './stores/session.js';
import {routes,page} from './router/index.js';
import {values} from './hooks/form.js';
import {esc} from './utils/html.js';
import * as settlements from './pages/settlements.js';
import * as layout from './pages/layout.js';
import * as pivot from './pages/pivot.js';
import * as reviews from './pages/reviews.js';
const root=document.querySelector('#app');
let flash='';
function feedback(text){flash=text;const el=document.querySelector('#error');if(el)el.textContent=text}
function run(fn){return Promise.resolve().then(fn).catch(e=>feedback(e.message))}
const PAGES=[settlements,layout,pivot,reviews];
async function load(){
 const [perfs,pivots,reviews,splits]=await Promise.all([
  api('/performances'),api('/pivots'),api('/reviews'),api('/splits')]);
 state.perfs=perfs;state.pivots=pivots;state.reviews=reviews;state.splits=splits;
 state.selected=pivots.find(r=>r.id===state.selected?.id)||pivots[0]||null;
}
export function download(name,data){
 const u=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));
 const a=document.createElement('a');a.href=u;a.download=name;a.click();URL.revokeObjectURL(u);
}
function login(){
 root.innerHTML=`<div class="login"><section class="cover"><div class="eyebrow">YUN MU / SETTLEMENT PROGRAMME 012</div><h1>散场之后，<br>每一笔都有回声。</h1><p>云幕剧院 · 场次结算节目单<br>场次渠道 → 透视 → 冻结下钻 → 差异签核<br>三处场馆 / 多渠售票 / 分币守恒</p></section><section><div class="eyebrow">STAGE PIVOT</div><h2>登录结算节目单</h2><form id="login"><label>工作邮箱<input name="email" type="email" value="analyst@demo.local" required></label><label>密码<input name="password" type="password" value="Demo123!" required></label><button class="primary">进入场次结算</button></form><p id="error" class="error"></p><p>admin / analyst / viewer @demo.local<br>密码：Demo123!</p></section></div>`;
 document.querySelector('#login').onsubmit=e=>{e.preventDefault();run(async()=>{
  const d=await post('/auth/login',values(e.target));localStorage.setItem('token',d.token);
  state.user=d.user;await load();render();
 })};
}
function render(){
 const n=Math.min(3,Math.max(0,page()));
 root.innerHTML=`<header><div class="brand">云幕 / 场次结算节目单 <span class="eyebrow">STAGE PIVOT</span></div>
 <div>${esc(state.user.email)} · ${esc(state.user.role)} <button id="logout">退出</button></div></header>
 <nav>${routes.map((r,i)=>`<button data-nav="${i}" class="${i===n?'active':''}">0${i+1} ${r}</button>`).join('')}<span class="eyebrow">THEATRE ACCOUNTS / 2026</span></nav>
 <main><div class="intro"><div><div class="eyebrow">SETTLEMENT PROGRAMME / 0${n+1}</div><h1>${routes[n]}</h1>
 <p>让票款、退款与渠道费回到具体场次。同场多渠道共用座位，金额按渠道汇总，座位按场次去重。</p></div>
 <span class="tag">3 场馆 / 分币守恒</span></div>
 <p id="error" class="error">${esc(flash)}</p>${PAGES[n].render()}</main>`;
 flash='';
 bind();
 if(state.user.role==='viewer')document.querySelectorAll('form button,#draft-review,#split .primary,#perf .primary').forEach(b=>{
  b.disabled=true;b.textContent='观察员只读'});
}
const ctx={run,reload:async()=>{await load()},rerender:render,download,notify:feedback};
function bind(){
 document.querySelectorAll('[data-nav]').forEach(b=>b.onclick=()=>{location.hash=b.dataset.nav});
 document.querySelector('#logout').onclick=()=>{localStorage.removeItem('token');state.user=null;login()};
 const n=Math.min(3,Math.max(0,page()));
 PAGES[n].bind?.(ctx);
 }
window.onhashchange=()=>{if(state.user){render();try{window.scrollTo(0,0)}catch(e){}}};
if(localStorage.getItem('token'))run(async()=>{try{state.user=await api('/me');await load();render()}catch(e){localStorage.removeItem('token');login()}});
else login();
