from sqlalchemy import select
from fastapi import HTTPException
from src.models.entities import Performance,SplitDraft
from src.services.performances import (now,performance_dump,input_channels,
                                       validate_allocation,replace_channels,lock_performance)
from src.services.revisions import record_revision
def draft_dump(d,p=None):
 data={'id':d.id,'performance_id':d.performance_id,'base_version':d.base_version,'status':d.status,
       'channels':d.channels,'note':d.note,'applied_version':d.applied_version,
       'created':d.created,'updated':d.updated,'result':d.result}
 if p is not None:
  data['performance']=performance_dump(p)
  data['stale']=d.status=='draft' and d.base_version!=p.version
  data['seat_total']=p.seats
  data['checked_before']=sum(c['checked'] for c in d.channels)
 return data
def get_draft(s,i):
 d=s.get(SplitDraft,i)
 if not d:raise HTTPException(404,'拆分草稿不存在')
 p=s.get(Performance,d.performance_id)
 return draft_dump(d,p)
def _lock_draft(s,i):
 d=s.execute(select(SplitDraft).where(SplitDraft.id==i).with_for_update()).scalar_one_or_none()
 if not d:raise HTTPException(404,'拆分草稿不存在')
 return d
def create_draft(s,performance_id,data):
 p=lock_performance(s,performance_id,write=False)
 channels=input_channels(data.channels)
 if data.base_version!=p.version:
  raise HTTPException(409,'场次当前版本 %d 与草稿基准 %d 不一致，请刷新后重试'%(p.version,data.base_version))
 validate_allocation(channels,p.seats)
 if len(channels)<2:raise HTTPException(422,'拆分草稿至少需要两个渠道；单渠道修订请使用修订接口')
 d=SplitDraft(performance_id=p.id,base_version=data.base_version,status='draft',channels=channels,
              note=data.note,created=now(),updated=now())
 s.add(d);s.commit()
 return draft_dump(d,p)
def edit_draft(s,i,data):
 d=_lock_draft(s,i)
 if d.status!='draft':raise HTTPException(409,'已确认的拆分不可修改，请新建草稿')
 p=lock_performance(s,d.performance_id)
 channels=input_channels(data.channels)
 if len(channels)<2:raise HTTPException(422,'拆分草稿至少需要两个渠道；单渠道修订请使用修订接口')
 validate_allocation(channels,p.seats)
 d.channels=channels;d.note=data.note;d.updated=now()
 s.commit()
 return draft_dump(d,p)
def confirm_draft(s,i):
 d=_lock_draft(s,i)
 p=lock_performance(s,d.performance_id)
 if d.status=='confirmed':
  return draft_dump(d,p)
 if d.status!='draft':raise HTTPException(409,'拆分草稿状态不可确认')
 if d.base_version!=p.version:
  raise HTTPException(409,'草稿基于场次版本 %d，当前版本 %d，已过期；请刷新后新建拆分草稿'%(d.base_version,p.version))
 channels=[dict(c) for c in d.channels]
 validate_allocation(channels,p.seats)
 record_revision(s,p,'before_split')
 before=performance_dump(p)
 replace_channels(p,channels)
 p.version=p.version+1
 s.flush()
 after=performance_dump(p)
 d.status='confirmed';d.applied_version=p.version;d.updated=now()
 d.result={'draft_id':d.id,'performance_id':p.id,'before':before,'after':after,
           'before_version':before['version'],'after_version':after['version'],
           'atomic':True,'note':'整场渠道与座位在同一事务内原子替换'}
 s.commit()
 return draft_dump(d,p)
def list_drafts(s,performance_id=None):
 q=select(SplitDraft).order_by(SplitDraft.id.desc())
 if performance_id is not None:q=q.where(SplitDraft.performance_id==performance_id)
 ds=s.execute(q).scalars().all()
 ids={d.performance_id for d in ds}
 perfs={p.id:p for p in s.execute(select(Performance).where(Performance.id.in_(ids))).scalars().all()} if ids else {}
 return [draft_dump(d,perfs.get(d.performance_id)) for d in ds]
