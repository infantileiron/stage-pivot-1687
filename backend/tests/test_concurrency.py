from conftest import perf
from src.config.database import Session
from src.models.entities import Performance,SettlementChannel,SplitDraft
import src.services.splits as splits_mod
SPLIT=[{'channel':'剧院直营','gross_cents':3000,'refund_cents':0,'fee_cents':0,'checked':30},
       {'channel':'票务合作','gross_cents':2000,'refund_cents':0,'fee_cents':0,'checked':20}]
def _setup(client,seats=100):
 p=client.post('/performances',json=perf('P-1',seats=seats),headers=client.analyst).json()
 d=client.post('/performances/%d/splits'%p['id'],headers=client.analyst,
               json={'base_version':1,'channels':SPLIT}).json()
 return p,d
def test_failed_confirm_rolls_back_whole_performance(client,monkeypatch):
 p,d=_setup(client)
 orig=splits_mod.replace_channels
 calls={'n':0}
 def boom(perf_obj,channels):
  calls['n']+=1
  raise RuntimeError('模拟替换中途失败')
 monkeypatch.setattr(splits_mod,'replace_channels',boom)
 try:
  client.post('/splits/%d/confirm'%d['id'],headers=client.analyst)
 except Exception:pass
 monkeypatch.setattr(splits_mod,'replace_channels',orig)
 with Session() as s:
  row=s.get(Performance,p['id']);draft=s.get(SplitDraft,d['id'])
  assert row.version==1 and len(row.channels)==1 and row.channels[0].channel=='剧院直营'
  assert draft.status=='draft' and draft.applied_version is None
 # 仍然可以再次确认成功
 r=client.post('/splits/%d/confirm'%d['id'],headers=client.analyst)
 assert r.status_code==200 and r.json()['applied_version']==2
def test_pivot_never_sees_mixed_version(client):
 from src.services.performances import read_snapshot
 p,d=_setup(client)
 with Session() as s:before=read_snapshot(s)
 assert {r['performance_version'] for r in before}=={1}
 client.post('/splits/%d/confirm'%d['id'],headers=client.analyst)
 with Session() as s:after=read_snapshot(s)
 assert {r['performance_version'] for r in after}=={2}
 assert len(after)==2 and {r['channel'] for r in after}=={'剧院直营','票务合作'}
 assert all(r['seats']==100 for r in after)
def test_revision_history_and_restore(client):
 p=client.post('/performances',json=perf('P-1',seats=100),headers=client.analyst).json()
 body=perf('P-1',seats=120);body['expected_version']=1
 client.put('/performances/%d'%p['id'],json=body,headers=client.analyst)
 revs=client.get('/performances/%d/revisions'%p['id'],headers=client.analyst).json()
 assert [r['version'] for r in revs]==[1] and revs[0]['snapshot']['seats']==100
 restored=client.post('/performances/%d/revisions/%d/restore'%(p['id'],revs[0]['id']),
   json={'expected_version':2},headers=client.analyst)
 assert restored.status_code==200 and restored.json()['seats']==100 and restored.json()['version']==3
 stale=client.post('/performances/%d/revisions/%d/restore'%(p['id'],revs[0]['id']),
   json={'expected_version':2},headers=client.analyst)
 assert stale.status_code==409
def test_revision_history_capped(client):
 p=client.post('/performances',json=perf('P-1',seats=100),headers=client.analyst).json()
 version=1
 for i in range(25):
  body=perf('P-1',seats=100+i%5);body['expected_version']=version
  r=client.put('/performances/%d'%p['id'],json=body,headers=client.analyst)
  assert r.status_code==200,r.text
  version=r.json()['version']
 revs=client.get('/performances/%d/revisions'%p['id'],headers=client.analyst).json()
 assert len(revs)==20
def test_export_contains_channels_and_deduped_totals(client):
 p=client.post('/performances',json=perf('P-1',seats=100,channels=SPLIT),headers=client.analyst).json()
 client.post('/performances',json=perf('P-2',seats=300,day='2026-11-16'),headers=client.analyst)
 d=client.get('/performances/export',headers=client.analyst).json()
 assert d['total']['performances']==2 and d['total']['channels']==3
 assert d['total']['seats']==400 and d['total']['checked']==90
 one=client.get('/performances/%d/export'%p['id'],headers=client.analyst).json()
 assert one['total']['channels']==2 and one['total']['net_cents']==5000
