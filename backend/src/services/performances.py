import json
from datetime import datetime,timezone
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import object_session
from src.models.entities import Performance,SettlementChannel
from src.schemas.business import PerformanceInput
from src.services.business import dump
def now():return datetime.now(timezone.utc).isoformat()
def channel_rows(p):
 return [{'channel':c.channel,'gross_cents':c.gross_cents,'refund_cents':c.refund_cents,
          'fee_cents':c.fee_cents,'checked':c.checked} for c in sorted(p.channels,key=lambda x:x.channel)]
def performance_dump(p):
 ch=channel_rows(p)
 return {'id':p.id,'code':p.code,'day':p.day,'venue':p.venue,'play':p.play,'seats':p.seats,
         'version':p.version,'channels':ch,'checked_total':sum(c['checked'] for c in ch),
         'gross_cents':sum(c['gross_cents'] for c in ch),'refund_cents':sum(c['refund_cents'] for c in ch),
         'fee_cents':sum(c['fee_cents'] for c in ch),
         'net_cents':sum(c['gross_cents']-c['refund_cents']-c['fee_cents'] for c in ch),
         'channel_count':len(ch)}
def snapshot_rows(performances):
 rows=[]
 for p in performances:
  for c in p.channels:
   rows.append({'performance_id':p.id,'performance_version':p.version,'code':p.code,'day':p.day,
                'venue':p.venue,'play':p.play,'channel':c.channel,'gross_cents':c.gross_cents,
                'refund_cents':c.refund_cents,'fee_cents':c.fee_cents,'seats':p.seats,'checked':c.checked})
 return sorted(rows,key=lambda r:(r['code'],r['channel']))
def export_payload(performances):
 rows=snapshot_rows(performances)
 return {'exported':now(),'performances':[performance_dump(p) for p in performances],
         'channels':rows,'total':{'performances':len(performances),'channels':len(rows),
         'seats':sum(p.seats for p in performances),
         'checked':sum(c.checked for p in performances for c in p.channels),
         'net_cents':sum(c.gross_cents-c.refund_cents-c.fee_cents for p in performances for c in p.channels)}}
def input_channels(channels):
 return [{'channel':c.channel,'gross_cents':c.gross_cents,'refund_cents':c.refund_cents,
          'fee_cents':c.fee_cents,'checked':c.checked} for c in channels]
def validate_allocation(channels,seats):
 names=[c['channel'] for c in channels]
 if not names:raise HTTPException(422,'至少保留一个售票渠道')
 if len(set(names))!=len(names):raise HTTPException(422,'同一场次的渠道必须唯一，请合并重复渠道')
 if any(c['refund_cents']+c['fee_cents']>c['gross_cents'] for c in channels):
  raise HTTPException(422,'退款与渠道费合计不得超过该渠道票款')
 total=sum(c['checked'] for c in channels)
 if total>seats:raise HTTPException(422,'各渠道核验合计 %d 人超过座位 %d 人，请缩减核验或增加座位'%(total,seats))
def replace_channels(p,channels):
 # 先删除旧渠道并 flush，再插入新渠道，避开 (performance_id, channel) 唯一键在同一事务内的先插后删冲突。
 p.channels.clear()
 session=object_session(p)
 if session is not None:session.flush()
 p.channels[:]=[SettlementChannel(**c) for c in channels]
def lock_performance(s,i,write=True):
 stmt=select(Performance).where(Performance.id==i)
 stmt=stmt.with_for_update() if write else stmt.with_for_update(read=True)
 p=s.execute(stmt).scalar_one_or_none()
 if not p:raise HTTPException(404,'场次不存在')
 list(p.channels)
 return p
def read_snapshot(s):
 # 单条 JOIN 查询在同一读快照内取场次版本与渠道行，避免读到“场馆已换版本、渠道仍是旧行”的
 # 半完成状态；确认拆分在同一事务整场替换，透视只会看到替换前或替换后的完整版本。
 rows=s.execute(select(Performance.id,Performance.version,Performance.code,Performance.day,
                       Performance.venue,Performance.play,Performance.seats,
                       SettlementChannel.channel,SettlementChannel.gross_cents,
                       SettlementChannel.refund_cents,SettlementChannel.fee_cents,SettlementChannel.checked)
                .join(SettlementChannel,SettlementChannel.performance_id==Performance.id)
                .order_by(Performance.id,SettlementChannel.channel)).all()
 return [{'performance_id':r[0],'performance_version':r[1],'code':r[2],'day':r[3],'venue':r[4],
          'play':r[5],'seats':r[6],'channel':r[7],'gross_cents':r[8],'refund_cents':r[9],
          'fee_cents':r[10],'checked':r[11]} for r in rows]
def create_performance(s,data):
 channels=input_channels(data.channels);validate_allocation(channels,data.seats)
 p=Performance(code=data.code,day=data.day.isoformat(),venue=data.venue,play=data.play,seats=data.seats,version=1)
 replace_channels(p,channels);s.add(p)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'场次编号重复，一场次仅一条结算')
 return performance_dump(p)
def edit_performance(s,data,i):
 p=lock_performance(s,i)
 if data.expected_version!=p.version:
  raise HTTPException(409,'场次已被其他操作修订（当前版本 %d，提交版本 %d），请刷新后重试'%(p.version,data.expected_version))
 channels=input_channels(data.channels);validate_allocation(channels,data.seats)
 from src.services.revisions import record_revision
 record_revision(s,p,'before_edit')
 p.day=data.day.isoformat();p.venue=data.venue;p.play=data.play;p.seats=data.seats
 replace_channels(p,channels);p.version=p.version+1;s.commit()
 return performance_dump(p)
def legacy_create(s,data):
 return create_performance(s,PerformanceInput(code=data.code,day=data.day,venue=data.venue,play=data.play,
  seats=data.seats,channels=[{'channel':data.channel,'gross_cents':data.gross_cents,'refund_cents':data.refund_cents,
  'fee_cents':data.fee_cents,'checked':data.checked}]))
def legacy_edit(s,data,i):
 p=lock_performance(s,i)
 if len(p.channels)>1:
  raise HTTPException(409,'该场次已拆分多渠道，旧版单渠道接口不能覆盖，请使用场次修订与拆分接口')
 if data.expected_version is not None and data.expected_version!=p.version:
  raise HTTPException(409,'场次已被其他操作修订（当前版本 %d），请刷新后重试'%p.version)
 channels=[{'channel':data.channel,'gross_cents':data.gross_cents,'refund_cents':data.refund_cents,
            'fee_cents':data.fee_cents,'checked':data.checked}]
 validate_allocation(channels,data.seats)
 from src.services.revisions import record_revision
 record_revision(s,p,'before_edit')
 p.day=data.day.isoformat();p.venue=data.venue;p.play=data.play;p.seats=data.seats
 replace_channels(p,channels);p.version=p.version+1;s.commit()
 return performance_dump(p)
