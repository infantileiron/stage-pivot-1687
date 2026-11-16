import json,hashlib
DIMENSIONS={'venue','play','channel','month'}
MONEY=('gross_cents','refund_cents','fee_cents')
SUMS=(*MONEY,'checked')
def key(row,dim):return row['day'][:7] if dim=='month' else row[dim]
def _validate(rows):
 if not rows:raise ValueError('没有结算记录，请先录入场次')
 seen=set();seats={};perf_checked={}
 for r in rows:
  if 'code' not in r or 'channel' not in r:raise ValueError('结算快照缺少场次或渠道字段')
  code,channel=r['code'],r['channel']
  if (code,channel) in seen:raise ValueError('同一场次的渠道重复，无法保证结算守恒')
  seen.add((code,channel))
  for k in ('seats','checked'):
   if not isinstance(r.get(k),int) or isinstance(r.get(k),bool) or not 0<=r[k]<=10000:raise ValueError('座位与核验人数必须为0–10000的整数')
  for k in MONEY:
   if not isinstance(r.get(k),int) or isinstance(r.get(k),bool) or r[k]<0:raise ValueError('票款、退款与费用必须为非负整数分')
  if r['refund_cents']+r['fee_cents']>r['gross_cents']:raise ValueError('退款与渠道费合计不得超过该渠道票款')
  if seats.setdefault(code,r['seats'])!=r['seats']:raise ValueError('同一场次的座位数在各渠道间不一致')
  perf_checked[code]=perf_checked.get(code,0)+r['checked']
 for code,total in perf_checked.items():
  if total>seats[code]:raise ValueError('场次 %s 的各渠道核验合计超过座位数'%code)
def aggregate(rows):
 out={k:sum(r[k] for r in rows) for k in SUMS}
 perfs={r['code']:r['seats'] for r in rows}
 out['count']=len(perfs);out['seats']=sum(perfs.values())
 out['net_cents']=out['gross_cents']-out['refund_cents']-out['fee_cents']
 out['occupancy']=out['checked']/out['seats'] if out['seats'] else None
 return out
def pivot(rows,row_dim,col_dim):
 if row_dim not in DIMENSIONS or col_dim not in DIMENSIONS or row_dim==col_dim:raise ValueError('请选择两个不同的白名单维度')
 _validate(rows)
 row_keys=sorted({key(r,row_dim) for r in rows});col_keys=sorted({key(r,col_dim) for r in rows})
 cells=[{'row_key':a,'col_key':b,**aggregate([r for r in rows if key(r,row_dim)==a and key(r,col_dim)==b])} for a in row_keys for b in col_keys]
 row_totals=[{'key':a,**aggregate([r for r in rows if key(r,row_dim)==a])} for a in row_keys]
 col_totals=[{'key':b,**aggregate([r for r in rows if key(r,col_dim)==b])} for b in col_keys]
 total=aggregate(rows)
 additive_keys=(*MONEY,'net_cents','checked')
 additive_ok=all(sum(x[k] for x in cells)==sum(x[k] for x in row_totals)==sum(x[k] for x in col_totals)==total[k] for k in additive_keys)
 seats={r['code']:r['seats'] for r in rows}
 count_ok=total['count']==len(seats) and total['seats']==sum(seats.values())
 count_ok=count_ok and all(t['count']==len({r['code'] for r in rows if key(r,row_dim)==t['key']}) and t['seats']==sum({r['code']:r['seats'] for r in rows if key(r,row_dim)==t['key']}.values()) for t in row_totals)
 count_ok=count_ok and all(t['count']==len({r['code'] for r in rows if key(r,col_dim)==t['key']}) and t['seats']==sum({r['code']:r['seats'] for r in rows if key(r,col_dim)==t['key']}.values()) for t in col_totals)
 count_ok=count_ok and all(c['count']==len({r['code'] for r in rows if key(r,row_dim)==c['row_key'] and key(r,col_dim)==c['col_key']}) for c in cells)
 within_ok=all(t['checked']<=t['seats'] for t in (*cells,*row_totals,*col_totals,total) if t['seats'])
 conservation={'money_additive':additive_ok,'performance_dedupe':count_ok,'checked_within_seats':within_ok}
 if not all(conservation.values()):raise ValueError('行列总计不守恒，请核对输入')
 versions=sorted((r['code'],r.get('performance_version',1)) for r in rows)
 return dict(row_keys=row_keys,col_keys=col_keys,cells=cells,row_totals=row_totals,col_totals=col_totals,total=total,
  conserved=True,conservation=conservation,
  version_checksum=hashlib.sha256(json.dumps(versions,ensure_ascii=False).encode()).hexdigest(),
  checksum=hashlib.sha256(json.dumps(sorted(rows,key=lambda r:(r['code'],r['channel'])),sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
  method='金额以整数分按渠道相加；净结算=票款−退款−渠道费。场次数与座位按场次编号去重：同一场次的多个渠道不重复计座，跨渠道的行、列与总计由原始渠道明细重新计算，不把各单元座位相加。核验人数按渠道相加，且每个场次各渠道核验合计不得超过座位。上座率=总核验/去重总座位，零座位未定义。月份按业务日期YYYY-MM；下钻始终读取冻结快照。')
