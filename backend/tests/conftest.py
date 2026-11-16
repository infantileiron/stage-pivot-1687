import os,sys
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/stage_pivot_test.db')
os.environ.setdefault('REDIS_URL','redis://localhost:6379/15')
os.environ.setdefault('JWT_SECRET','test-secret-3112')
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from fastapi.testclient import TestClient
from src.config.database import Base,engine,Session
from src.models.entities import User
from src.utils.security import hash_password
from src.services.analysis import pivot
import src.routes.api as routes
def _run_pivot(s,r):
 from src.models.entities import Pivot
 try:
  result=pivot(r.result['snapshot'],r.row_dim,r.col_dim)
  r.result={**result,'snapshot':r.result['snapshot']};r.state='done';r.error=''
 except Exception as e:
  r.state='failed';r.error=str(e)
 s.commit()
@pytest.fixture()
def client(monkeypatch):
 Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
 with Session() as s:
  for role in ('admin','analyst','viewer'):
   s.add(User(email=role+'@t.local',role=role,password=hash_password('pw')))
  s.commit()
 monkeypatch.setattr(routes,'queue_pivot',_run_pivot)
 from src.main import app
 c=TestClient(app)
 def login(role):
  r=c.post('/auth/login',json={'email':role+'@t.local','password':'pw'})
  assert r.status_code==200,r.text
  return {'Authorization':'Bearer '+r.json()['token']}
 c.analyst=login('analyst');c.admin=login('admin');c.viewer=login('viewer')
 return c
def perf(code='P-1',seats=100,day='2026-11-15',venue='云幕大剧场',play='渡口来信',channels=None):
 return {'code':code,'day':day,'venue':venue,'play':play,'seats':seats,
         'channels':channels or [{'channel':'剧院直营','gross_cents':5000,'refund_cents':0,'fee_cents':0,'checked':40}]}
