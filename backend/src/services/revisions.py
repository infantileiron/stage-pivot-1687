from sqlalchemy import select
from fastapi import HTTPException
from src.models.entities import PerformanceRevision
from src.services.performances import (now,performance_dump,validate_allocation,
                                       replace_channels,lock_performance)
REVISION_LIMIT=20
def record_revision(s,p,action):
 s.add(PerformanceRevision(performance_id=p.id,version=p.version,action=action,
                           snapshot=performance_dump(p),created=now()))
 s.flush()
 old=s.execute(select(PerformanceRevision).where(PerformanceRevision.performance_id==p.id)
               .order_by(PerformanceRevision.version.desc()).offset(REVISION_LIMIT)).scalars().all()
 for r in old:s.delete(r)
def revisions(s,performance_id):
 rs=s.execute(select(PerformanceRevision).where(PerformanceRevision.performance_id==performance_id)
              .order_by(PerformanceRevision.version.desc())).scalars().all()
 return [{'id':r.id,'performance_id':r.performance_id,'version':r.version,'action':r.action,
          'snapshot':r.snapshot,'created':r.created} for r in rs]
def revision(s,revision_id):
 return s.get(PerformanceRevision,revision_id)
def apply_revision(s,revision_id,expected_version):
 rev=revision(s,revision_id)
 if not rev:raise HTTPException(404,'历史版本不存在')
 p=lock_performance(s,rev.performance_id)
 if expected_version!=p.version:
  raise HTTPException(409,'场次已被其他操作修订（当前版本 %d），请刷新后重试'%p.version)
 snap=rev.snapshot
 channels=[{k:c[k] for k in ('channel','gross_cents','refund_cents','fee_cents','checked')} for c in snap['channels']]
 validate_allocation(channels,snap['seats'])
 p.day=snap['day'];p.venue=snap['venue'];p.play=snap['play'];p.seats=snap['seats']
 replace_channels(p,channels);p.version=p.version+1;s.commit()
 return performance_dump(p)
