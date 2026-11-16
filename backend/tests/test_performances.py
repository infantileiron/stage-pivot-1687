from conftest import perf
def test_create_and_list_performance_with_channels(client):
 r=client.post('/performances',json=perf(channels=[
  {'channel':'剧院直营','gross_cents':5000,'refund_cents':100,'fee_cents':50,'checked':40},
  {'channel':'票务合作','gross_cents':3000,'refund_cents':0,'fee_cents':100,'checked':30},
 ]),headers=client.analyst)
 assert r.status_code==200,r.text
 d=r.json()
 assert d['code']=='P-1' and d['channel_count']==2 and d['version']==1
 assert d['checked_total']==70 and d['net_cents']==5000-100-50+3000-0-100
 rows=client.get('/performances',headers=client.analyst).json()
 assert rows[0]['channels'][0]['channel']=='剧院直营'
def test_duplicate_channel_rejected(client):
 body=perf(channels=[
  {'channel':'剧院直营','gross_cents':1000,'refund_cents':0,'fee_cents':0,'checked':10},
  {'channel':'剧院直营','gross_cents':1000,'refund_cents':0,'fee_cents':0,'checked':10},
 ])
 assert client.post('/performances',json=body,headers=client.analyst).status_code==422
def test_checked_over_seats_rejected_across_channels(client):
 body=perf(seats=50,channels=[
  {'channel':'剧院直营','gross_cents':1000,'refund_cents':0,'fee_cents':0,'checked':40},
  {'channel':'票务合作','gross_cents':1000,'refund_cents':0,'fee_cents':0,'checked':20},
 ])
 r=client.post('/performances',json=body,headers=client.analyst)
 assert r.status_code==422 and ('超过座位' in r.text or '不得超过' in r.text)
def test_duplicate_code_conflict(client):
 assert client.post('/performances',json=perf(),headers=client.analyst).status_code==200
 assert client.post('/performances',json=perf(),headers=client.analyst).status_code==409
def test_viewer_cannot_write(client):
 assert client.post('/performances',json=perf(),headers=client.viewer).status_code==403
def test_versioned_edit_rejects_stale(client):
 d=client.post('/performances',json=perf(),headers=client.analyst).json()
 body=perf();body['expected_version']=1
 ok=client.put('/performances/%d'%d['id'],json=body,headers=client.analyst)
 assert ok.status_code==200 and ok.json()['version']==2
 stale=client.put('/performances/%d'%d['id'],json=body,headers=client.analyst)
 assert stale.status_code==409
def test_edit_cannot_shrink_seats_below_checked(client):
 d=client.post('/performances',json=perf(seats=100),headers=client.analyst).json()
 body=perf(seats=20);body['expected_version']=1
 r=client.put('/performances/%d'%d['id'],json=body,headers=client.analyst)
 assert r.status_code==422 and ('超过座位' in r.text or '不得超过' in r.text)
 assert client.get('/performances/%d'%d['id'],headers=client.analyst).json()['seats']==100
