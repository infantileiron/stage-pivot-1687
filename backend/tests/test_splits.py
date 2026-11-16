from conftest import perf
SPLIT=[{'channel':'剧院直营','gross_cents':3000,'refund_cents':0,'fee_cents':0,'checked':30},
       {'channel':'票务合作','gross_cents':2000,'refund_cents':0,'fee_cents':0,'checked':20}]
def _create(client,seats=100):
 return client.post('/performances',json=perf(seats=seats),headers=client.analyst).json()
def test_split_draft_to_confirm_atomic(client):
 p=_create(client)
 draft=client.post('/performances/%d/splits'%p['id'],headers=client.analyst,
                   json={'base_version':1,'channels':SPLIT,'note':'拆两渠道'})
 assert draft.status_code==200,draft.text
 d=draft.json()
 assert d['status']=='draft' and len(d['channels'])==2 and d['stale'] is False
 assert client.get('/performances/%d'%p['id'],headers=client.analyst).json()['channel_count']==1
 confirm=client.post('/splits/%d/confirm'%d['id'],headers=client.analyst)
 assert confirm.status_code==200,confirm.text
 cd=confirm.json()
 assert cd['status']=='confirmed' and cd['applied_version']==2
 p2=client.get('/performances/%d'%p['id'],headers=client.analyst).json()
 assert p2['version']==2 and p2['channel_count']==2 and p2['checked_total']==50
 assert cd['result']['before']['channel_count']==1 and cd['result']['after']['channel_count']==2
def test_confirm_is_idempotent(client):
 p=_create(client)
 d=client.post('/performances/%d/splits'%p['id'],headers=client.analyst,
               json={'base_version':1,'channels':SPLIT}).json()
 first=client.post('/splits/%d/confirm'%d['id'],headers=client.analyst).json()
 second=client.post('/splits/%d/confirm'%d['id'],headers=client.analyst).json()
 assert first['applied_version']==second['applied_version']==2
 assert client.get('/performances/%d'%p['id'],headers=client.analyst).json()['version']==2
 assert len(client.get('/performances/%d'%p['id'],headers=client.analyst).json()['channels'])==2
def test_confirmed_draft_not_editable(client):
 p=_create(client)
 d=client.post('/performances/%d/splits'%p['id'],headers=client.analyst,
               json={'base_version':1,'channels':SPLIT}).json()
 client.post('/splits/%d/confirm'%d['id'],headers=client.analyst)
 r=client.put('/splits/%d'%d['id'],headers=client.analyst,json={'channels':SPLIT,'note':'x'*10})
 assert r.status_code==409
def test_stale_draft_confirm_rejected_after_performance_edit(client):
 p=_create(client)
 d=client.post('/performances/%d/splits'%p['id'],headers=client.analyst,
               json={'base_version':1,'channels':SPLIT}).json()
 body=perf();body['expected_version']=1
 assert client.put('/performances/%d'%p['id'],json=body,headers=client.analyst).status_code==200
 r=client.post('/splits/%d/confirm'%d['id'],headers=client.analyst)
 assert r.status_code==409 and '过期' in r.text
 listed=client.get('/splits?performance_id=%d'%p['id'],headers=client.analyst).json()
 assert listed[0]['stale'] is True
def test_draft_rejects_checked_over_seats(client):
 p=_create(client,seats=40)
 r=client.post('/performances/%d/splits'%p['id'],headers=client.analyst,
               json={'base_version':1,'channels':SPLIT})
 assert r.status_code==422
def test_confirm_rejects_when_seats_shrunk_after_draft(client):
 p=_create(client,seats=100)
 d=client.post('/performances/%d/splits'%p['id'],headers=client.analyst,
               json={'base_version':1,'channels':SPLIT}).json()
 body=perf(seats=45);body['expected_version']=1
 shrunk=client.put('/performances/%d'%p['id'],json=body,headers=client.analyst)
 assert shrunk.status_code==200,shrunk.text  # 40 核验仍 ≤ 45 座位
 r=client.post('/splits/%d/confirm'%d['id'],headers=client.analyst)
 assert r.status_code==409
def test_confirm_revalidates_allocation_when_base_version_still_matches(client):
 p=_create(client,seats=100)
 d=client.post('/performances/%d/splits'%p['id'],headers=client.analyst,
               json={'base_version':1,'channels':SPLIT}).json()
 # 直接改库模拟并发缩减座位但不抬版本（例如迁移/维护窗口），确认时仍拒绝超额
 from src.config.database import Session
 from src.models.entities import Performance
 with Session() as s:
  s.get(Performance,p['id']).seats=40;s.commit()
 r=client.post('/splits/%d/confirm'%d['id'],headers=client.analyst)
 assert r.status_code==422 and ('超过座位' in r.text or '不得超过' in r.text)
 assert client.get('/performances/%d'%p['id'],headers=client.analyst).json()['channel_count']==1
def test_viewer_cannot_confirm_split(client):
 p=_create(client)
 d=client.post('/performances/%d/splits'%p['id'],headers=client.analyst,
               json={'base_version':1,'channels':SPLIT}).json()
 assert client.post('/splits/%d/confirm'%d['id'],headers=client.viewer).status_code==403
