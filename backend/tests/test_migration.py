from sqlalchemy import text
from src.config.database import Session,engine
from src.models.entities import Performance,Pivot
from src.services.migration import migrate_legacy
from conftest import perf
LEGACY_DDL='''CREATE TABLE settlements (id INTEGER PRIMARY KEY AUTOINCREMENT, code VARCHAR(60) NOT NULL UNIQUE,
 day VARCHAR(10), venue VARCHAR(40), play VARCHAR(60), channel VARCHAR(30), gross_cents BIGINT,
 refund_cents BIGINT, fee_cents BIGINT, seats INTEGER, checked INTEGER)'''
def _seed_legacy():
 with engine.begin() as c:
  c.execute(text('DROP TABLE IF EXISTS settlements'))
  c.execute(text(LEGACY_DDL))
  c.execute(text("INSERT INTO settlements(code,day,venue,play,channel,gross_cents,refund_cents,fee_cents,seats,checked) VALUES "
                 "('OLD-1','2026-10-05','云幕大剧场','渡口来信','剧院直营',100000,10000,5000,100,80)"))
  c.execute(text("INSERT INTO settlements(code,day,venue,play,channel,gross_cents,refund_cents,fee_cents,seats,checked) VALUES "
                 "('OLD-2','2026-10-06','河畔小剧场','星河漫游','票务合作',50000,0,2500,240,150)"))
def test_legacy_rows_migrate_to_single_channel_performances(client):
 _seed_legacy()
 res=migrate_legacy()
 assert res=={'migrated':2,'skipped':False}
 with Session() as s:
  p=s.query(Performance).filter_by(code='OLD-1').one()
  assert p.version==1 and p.seats==100 and p.day=='2026-10-05'
  assert len(p.channels)==1 and p.channels[0].channel=='剧院直营'
  assert p.channels[0].gross_cents==100000 and p.channels[0].checked==80
def test_legacy_migration_idempotent(client):
 _seed_legacy()
 assert migrate_legacy()['migrated']==2
 assert migrate_legacy()['migrated']==0
 with Session() as s:assert s.query(Performance).count()==2
def test_history_pivot_and_review_still_readable_after_migration(client):
 _seed_legacy();migrate_legacy()
 # 伪造迁移前冻结的旧格式透视：快照为旧单渠道行，无 performance_version
 old_result={'snapshot':[{'code':'OLD-1','day':'2026-10-05','venue':'云幕大剧场','play':'渡口来信',
   'channel':'剧院直营','gross_cents':100000,'refund_cents':10000,'fee_cents':5000,'seats':100,'checked':80}],
   'row_keys':['云幕大剧场'],'col_keys':['剧院直营'],
   'cells':[{'row_key':'云幕大剧场','col_key':'剧院直营','gross_cents':100000,'refund_cents':10000,
             'fee_cents':5000,'seats':100,'checked':80,'count':1,'net_cents':85000,'occupancy':0.8}],
   'row_totals':[{'key':'云幕大剧场','gross_cents':100000,'refund_cents':10000,'fee_cents':5000,'seats':100,
                  'checked':80,'count':1,'net_cents':85000,'occupancy':0.8}],
   'col_totals':[{'key':'剧院直营','gross_cents':100000,'refund_cents':10000,'fee_cents':5000,'seats':100,
                  'checked':80,'count':1,'net_cents':85000,'occupancy':0.8}],
   'total':{'gross_cents':100000,'refund_cents':10000,'fee_cents':5000,'seats':100,'checked':80,'count':1,
            'net_cents':85000,'occupancy':0.8},'conserved':True,'checksum':'legacy','method':'旧版口径'}
 with Session() as s:
  p=Pivot(name='历史透视',row_dim='venue',col_dim='channel',state='done',result=old_result,error='')
  s.add(p);s.commit();pid=p.id
 d=client.get('/pivots/%d'%pid,headers=client.analyst).json()
 assert d['state']=='done' and d['result']['total']['net_cents']==85000
 assert d['result']['cells'][0]['occupancy']==0.8
 drill=client.get('/pivots/%d/drill'%pid,params={'row_key':'云幕大剧场','col_key':'剧院直营'},headers=client.analyst).json()
 assert drill['rows'][0]['code']=='OLD-1'
 export=client.get('/pivots/%d/export'%pid,headers=client.analyst)
 assert export.status_code==200 and 'stage-pivot-%d.json'%pid in export.headers['content-disposition']
 review=client.post('/reviews',headers=client.analyst,json={'pivot_id':pid,'row_key':'云幕大剧场',
   'col_key':'剧院直营','expected_cents':86000,'note':'旧透视仍可起草差异复核'})
 assert review.status_code==200 and review.json()['book_cents']==85000
 assert review.json()['difference_cents']==1000
def test_migration_requires_admin(client):
 _seed_legacy()
 assert client.post('/migrations/legacy',headers=client.analyst).status_code==403
 assert client.post('/migrations/legacy',headers=client.admin).json()['migrated']==2
def test_legacy_api_still_accepts_single_channel_write(client):
 body={'code':'L-9','day':'2026-11-15','venue':'云幕大剧场','play':'旧接口','channel':'剧院直营',
       'gross_cents':1000,'refund_cents':0,'fee_cents':0,'seats':10,'checked':5}
 r=client.post('/settlements',json=body,headers=client.analyst)
 assert r.status_code==200 and r.json()['channels'][0]['channel']=='剧院直营'
 rows=client.get('/settlements',headers=client.analyst).json()
 assert rows[0]['channel']=='剧院直营' and rows[0]['seats']==10
def test_legacy_edit_cannot_overwrite_split_performance(client):
 p=client.post('/performances',json=perf('S-1',seats=100),headers=client.analyst).json()
 d=client.post('/performances/%d/splits'%p['id'],headers=client.analyst,json={'base_version':1,'channels':[
  {'channel':'剧院直营','gross_cents':3000,'refund_cents':0,'fee_cents':0,'checked':30},
  {'channel':'票务合作','gross_cents':2000,'refund_cents':0,'fee_cents':0,'checked':20}]}).json()
 client.post('/splits/%d/confirm'%d['id'],headers=client.analyst)
 body={'code':'S-1','day':'2026-11-15','venue':'云幕大剧场','play':'覆盖','channel':'剧院直营',
       'gross_cents':1,'refund_cents':0,'fee_cents':0,'seats':10,'checked':1}
 r=client.put('/settlements/%d'%p['id'],json=body,headers=client.analyst)
 assert r.status_code==409 and '多渠道' in r.text
