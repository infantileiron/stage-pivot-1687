import {state} from '../stores/session.js';
import {esc} from '../utils/html.js';
import {badge} from '../components/common/status.js';
import {table} from '../components/common/table.js';
import {money,pct} from '../utils/format.js';
import {CHANNELS} from '../constants/enums.js';
export function channelEditor(channels,{seatLimit=null,prefix='ch'}={}){
 const checked=channels.reduce((a,c)=>a+Number(c.checked||0),0);
 const over=seatLimit!==null&&checked>seatLimit;
 return `<fieldset class="channels" data-seat-limit="${seatLimit??''}">
 <legend>渠道明细 <small>同场渠道唯一；核验合计 <b class="checked-sum">${checked}</b> <span class="seat-cap">${seatLimit!==null?`/ 座位 ${seatLimit}`:''}</span></small></legend>
 ${over?`<p class="error">各渠道核验合计 ${checked} 超过座位 ${seatLimit}，保存将被拒绝。</p>`:''}
 ${channels.map((c,i)=>`<div class="channel-row">
  <label>渠道<select name="${prefix}_channel_${i}">${CHANNELS.map(x=>`<option value="${esc(x)}"${x===c.channel?' selected':''}>${esc(x)}</option>`).join('')}</select></label>
  <label>票款 / 分<input name="${prefix}_gross_${i}" type="number" min="0" step="1" required value="${c.gross_cents??0}"></label>
  <label>退款 / 分<input name="${prefix}_refund_${i}" type="number" min="0" step="1" required value="${c.refund_cents??0}"></label>
  <label>渠道费 / 分<input name="${prefix}_fee_${i}" type="number" min="0" step="1" required value="${c.fee_cents??0}"></label>
  <label>核验<input name="${prefix}_checked_${i}" type="number" min="0" step="1" required value="${c.checked??0}"></label>
  <button type="button" data-remove-channel="${i}" class="ghost">移除</button>
 </div>`).join('')}
 <button type="button" data-add-channel="${channels.length}">增加渠道</button>
 </fieldset>`;
}
export function readChannels(form,{prefix='ch'}={}){
 const out=[];let i=0;
 while(form.querySelector(`[name="${prefix}_channel_${i}"]`)){
  out.push({channel:form.querySelector(`[name="${prefix}_channel_${i}"]`).value,
   gross_cents:Number(form.querySelector(`[name="${prefix}_gross_${i}"]`).value),
   refund_cents:Number(form.querySelector(`[name="${prefix}_refund_${i}"]`).value),
   fee_cents:Number(form.querySelector(`[name="${prefix}_fee_${i}"]`).value),
   checked:Number(form.querySelector(`[name="${prefix}_checked_${i}"]`).value)});
  i++;
 }
 return out;
}
export function channelTable(channels){
 return `<div class="scroll"><table class="channel-table"><thead><tr><th>渠道</th><th>票款 ¥</th><th>退款 ¥</th><th>渠道费 ¥</th><th>净额 ¥</th><th>核验</th></tr></thead><tbody>
 ${channels.map(c=>`<tr><td>${esc(c.channel)}</td><td>${money(c.gross_cents)}</td><td>${money(c.refund_cents)}</td><td>${money(c.fee_cents)}</td><td>${money(c.gross_cents-c.refund_cents-c.fee_cents)}</td><td>${c.checked}</td></tr>`).join('')||'<tr><td colspan="6">暂无渠道</td></tr>'}
 </tbody></table></div>`;
}
