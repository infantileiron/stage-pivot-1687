import os,time,json,logging
from pathlib import Path
import redis
from src.config.database import Session
from src.models.entities import Pivot
from src.services.analysis import pivot
q=redis.Redis.from_url(os.environ['REDIS_URL'])
def recover():
 with Session() as s:
  for r in s.query(Pivot).filter(Pivot.state.in_(['queued','running'])).all():r.state='queued';q.rpush('stage:pivots',r.id)
  s.commit()
def run(item):
 with Session() as s:
  r=s.get(Pivot,int(item))
  if not r or r.state!='queued':return
  snapshot=r.result['snapshot'];r.state='running';s.commit()
  try:
   result=pivot(snapshot,r.row_dim,r.col_dim)
   r.result={**result,'snapshot':snapshot};r.state='done';r.error=''
   Path('/artifacts/'+str(r.id)+'.json').write_text(json.dumps(r.result,ensure_ascii=False,indent=2))
  except Exception as e:
   r.state='failed';r.error=str(e)
  s.commit()
recover()
while True:
 Path('/tmp/heartbeat').touch()
 try:
  item=q.blpop('stage:pivots',timeout=3)
  if item:run(item[1])
 except Exception:logging.exception('worker');time.sleep(2)
