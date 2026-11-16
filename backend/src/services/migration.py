from sqlalchemy import inspect,text
from src.config.database import engine,Session
from src.models.entities import Performance,SettlementChannel
from src.constants.enums import CHANNELS
LEGACY_TABLE='settlements'
def migrate_legacy():
 """旧版一行一场次的 settlements 转为 performances + settlement_channels 单渠道场次。

 迁移只新增场次与渠道，不触碰 pivots/reviews；历史透视与复核仍按原冻结快照读取。
 以 code 幂等，重复执行不会重复入账。
 """
 insp=inspect(engine)
 if LEGACY_TABLE not in insp.get_table_names():return {'migrated':0,'skipped':True,'reason':'旧表不存在'}
 cols={c['name'] for c in insp.get_columns(LEGACY_TABLE)}
 required={'code','day','venue','play','channel','gross_cents','refund_cents','fee_cents','seats','checked'}
 if not required<=cols:return {'migrated':0,'skipped':True,'reason':'旧表字段不完整'}
 with engine.connect() as conn:
  rows=conn.execute(text('SELECT code,day,venue,play,channel,gross_cents,refund_cents,fee_cents,seats,checked FROM settlements ORDER BY id')).mappings().all()
 with Session() as s:
  existing={code for (code,) in s.query(Performance.code).all()}
  migrated=0
  for r in rows:
   if r['code'] in existing:continue
   channel=(r['channel'] or '').strip() or CHANNELS[0]
   p=Performance(code=r['code'],day=r['day'],venue=r['venue'],play=r['play'],
                 seats=int(r['seats'] or 0),version=1)
   p.channels=[SettlementChannel(channel=channel,gross_cents=int(r['gross_cents'] or 0),
                                 refund_cents=int(r['refund_cents'] or 0),fee_cents=int(r['fee_cents'] or 0),
                                 checked=int(r['checked'] or 0))]
   s.add(p);existing.add(r['code']);migrated+=1
  s.commit()
 return {'migrated':migrated,'skipped':False}
def legacy_row(p):
 channels=p.channels
 return {'id':p.id,'code':p.code,'day':p.day,'venue':p.venue,'play':p.play,
         'channel':channels[0].channel if len(channels)==1 else '多渠道',
         'gross_cents':sum(c.gross_cents for c in channels),
         'refund_cents':sum(c.refund_cents for c in channels),
         'fee_cents':sum(c.fee_cents for c in channels),
         'seats':p.seats,'checked':sum(c.checked for c in channels),
         'version':p.version,'channel_count':len(channels)}
