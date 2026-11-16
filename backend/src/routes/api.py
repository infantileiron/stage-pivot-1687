import os,json
import redis
from fastapi import APIRouter,Depends,HTTPException,Response
from src.config.database import db
from src.models.entities import User,Performance,Pivot,Review,Audit
from src.schemas.business import (Login,PerformanceInput,PerformanceEdit,LegacySettlementInput,
                                  LegacySettlementEdit,SplitDraftInput,SplitDraftEdit,RevisionApply,
                                  PivotInput,ReviewInput,ReviewEdit)
from src.middlewares.auth import current,editor,admin
from src.utils.security import verify,token
from src.services.business import audit,dump
from src.services.performances import (create_performance,edit_performance,legacy_create,legacy_edit,
                                       performance_dump,read_snapshot)
from src.services.splits import create_draft,edit_draft,confirm_draft,list_drafts
from src.services.revisions import revisions,apply_revision
from src.services.migration import migrate_legacy
from src.controllers.business import ensure_pivot,ensure_review,cell
from src.services.analysis import key
router=APIRouter()
def inline_pivot(s,r):
 from src.services.analysis import pivot
 try:
  result=pivot(r.result['snapshot'],r.row_dim,r.col_dim)
  r.result={**result,'snapshot':r.result['snapshot']};r.state='done';r.error=''
 except Exception as e:
  r.state='failed';r.error=str(e)
 s.commit()
def queue_pivot(s,r):
 url=os.environ['REDIS_URL']
 if url.startswith('inline://'):
  return inline_pivot(s,r)
 try:redis.Redis.from_url(url).rpush('stage:pivots',r.id)
 except redis.RedisError:
  r.state='failed';r.error='队列暂不可用，请恢复后新建透视';s.commit();raise HTTPException(503,r.error)
@router.post('/auth/login')
def login(data:Login,s=Depends(db)):
 u=s.query(User).filter_by(email=data.email).first()
 if not u or not verify(data.password,u.password):raise HTTPException(401,'账号或密码错误')
 return {'token':token(u),'user':dump(u)}
@router.get('/me')
def me(u=Depends(current)):return dump(u)

# 场次与渠道
@router.get('/performances')
def performances(u=Depends(current),s=Depends(db)):
 return [performance_dump(p) for p in s.query(Performance).order_by(Performance.id).all()]
@router.get('/performances/export')
def performances_export(u=Depends(current),s=Depends(db)):
 ps=s.query(Performance).order_by(Performance.id).all()
 from src.services.performances import export_payload
 return Response(json.dumps(export_payload(ps),ensure_ascii=False,indent=2),media_type='application/json',
                 headers={'Content-Disposition':'attachment; filename="performances-channels.json"'})
@router.get('/performances/{i}')
def performance(i:int,u=Depends(current),s=Depends(db)):
 p=s.get(Performance,i)
 if not p:raise HTTPException(404,'场次不存在')
 return performance_dump(p)
@router.post('/performances')
def create(data:PerformanceInput,u=Depends(editor),s=Depends(db)):
 r=create_performance(s,data);audit(s,u,'录入场次 '+r['code']+'，'+str(r['channel_count'])+' 渠道');return r
@router.put('/performances/{i}')
def edit(i:int,data:PerformanceEdit,u=Depends(editor),s=Depends(db)):
 r=edit_performance(s,data,i);audit(s,u,'修订场次 '+r['code']+' 至版本 '+str(r['version']));return r
@router.get('/performances/{i}/revisions')
def performance_revisions(i:int,u=Depends(current),s=Depends(db)):return revisions(s,i)
@router.post('/performances/{i}/revisions/{rid}/restore')
def restore_revision(i:int,rid:int,data:RevisionApply,u=Depends(editor),s=Depends(db)):
 r=apply_revision(s,rid,data.expected_version);audit(s,u,'恢复场次 '+r['code']+' 历史版本');return r
@router.get('/performances/{i}/export')
def performance_export(i:int,u=Depends(current),s=Depends(db)):
 p=s.get(Performance,i)
 if not p:raise HTTPException(404,'场次不存在')
 from src.services.performances import export_payload
 return Response(json.dumps(export_payload([p]),ensure_ascii=False,indent=2),media_type='application/json',
   headers={'Content-Disposition':f'attachment; filename="performance-{i}.json"'})

# 旧版单渠道兼容：便于旧客户端与旧数据继续录入
@router.get('/settlements')
def settlements(u=Depends(current),s=Depends(db)):
 from src.services.migration import legacy_row
 return [legacy_row(p) for p in s.query(Performance).order_by(Performance.id).all()]
@router.post('/settlements')
def settlement_create(data:LegacySettlementInput,u=Depends(editor),s=Depends(db)):
 r=legacy_create(s,data);audit(s,u,'录入结算 '+r['code']);return r
@router.put('/settlements/{i}')
def settlement_edit(i:int,data:LegacySettlementEdit,u=Depends(editor),s=Depends(db)):
 r=legacy_edit(s,data,i);audit(s,u,'修订结算 '+str(i));return r

# 拆分草稿
@router.get('/splits')
def splits(performance_id:int|None=None,u=Depends(current),s=Depends(db)):
 return list_drafts(s,performance_id)
@router.get('/splits/{i}')
def split_detail(i:int,u=Depends(current),s=Depends(db)):
 from src.services.splits import get_draft
 return get_draft(s,i)
@router.post('/performances/{i}/splits')
def split_create(i:int,data:SplitDraftInput,u=Depends(editor),s=Depends(db)):
 r=create_draft(s,i,data);audit(s,u,'起草拆分场次 '+r['performance']['code']);return r
@router.put('/splits/{i}')
def split_edit(i:int,data:SplitDraftEdit,u=Depends(editor),s=Depends(db)):
 r=edit_draft(s,i,data);audit(s,u,'修改拆分草稿 '+str(i));return r
@router.post('/splits/{i}/confirm')
def split_confirm(i:int,u=Depends(editor),s=Depends(db)):
 r=confirm_draft(s,i);audit(s,u,'确认拆分草稿 '+str(i)+'，场次版本 '+str(r['applied_version']));return r

# 旧数据迁移
@router.post('/migrations/legacy')
def migration(data:dict|None=None,u=Depends(admin),s=Depends(db)):
 result=migrate_legacy();audit(s,u,'迁移旧版单渠道结算：%s'%json.dumps(result,ensure_ascii=False));return result

# 透视
@router.get('/pivots')
def pivots(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Pivot).order_by(Pivot.id.desc()).all()]
@router.post('/pivots')
def submit(data:PivotInput,u=Depends(editor),s=Depends(db)):
 rows=read_snapshot(s)
 if not rows:raise HTTPException(409,'没有结算记录，请先录入场次')
 r=Pivot(**data.model_dump(),result={'snapshot':rows});s.add(r);s.commit();queue_pivot(s,r)
 audit(s,u,'提交透视 '+str(r.id));return dump(r)
@router.get('/pivots/{i}')
def detail(i:int,u=Depends(current),s=Depends(db)):return dump(ensure_pivot(s,i))
@router.get('/pivots/{i}/drill')
def drill(i:int,row_key:str,col_key:str,u=Depends(current),s=Depends(db)):
 r,c=cell(s,i,row_key,col_key)
 rows=[x for x in r.result['snapshot'] if key(x,r.row_dim)==row_key and key(x,r.col_dim)==col_key]
 return {'cell':c,'rows':rows}
@router.get('/pivots/{i}/export')
def export(i:int,u=Depends(current),s=Depends(db)):
 r=ensure_pivot(s,i)
 if r.state!='done':raise HTTPException(409,'仅成功透视可以导出')
 return Response(json.dumps(dump(r),ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="stage-pivot-{i}.json"'})
@router.get('/reviews')
def reviews(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Review).order_by(Review.id.desc()).all()]
@router.post('/reviews')
def review(data:ReviewInput,u=Depends(editor),s=Depends(db)):
 run,c=cell(s,data.pivot_id,data.row_key,data.col_key)
 r=Review(**data.model_dump(),book_cents=c['net_cents'],difference_cents=data.expected_cents-c['net_cents']);s.add(r);s.commit();audit(s,u,'起草差异复核 '+str(r.id));return dump(r)
@router.put('/reviews/{i}')
def edit_review(i:int,data:ReviewEdit,u=Depends(editor),s=Depends(db)):
 r=ensure_review(s,i)
 if r.status!='draft':raise HTTPException(409,'已签核复核单不可覆盖，请新建复核')
 r.expected_cents=data.expected_cents;r.difference_cents=data.expected_cents-r.book_cents;r.note=data.note;s.commit();audit(s,u,'修改差异复核 '+str(i));return dump(r)
@router.post('/reviews/{i}/approve')
def approve(i:int,u=Depends(admin),s=Depends(db)):
 r=ensure_review(s,i)
 if r.status!='draft':raise HTTPException(409,'已签核复核单不可重复签核')
 r.status='approved';s.commit();audit(s,u,'签核差异复核 '+str(i));return dump(r)
@router.get('/audits')
def audits(u=Depends(admin),s=Depends(db)):return [dump(r) for r in s.query(Audit).order_by(Audit.id.desc()).limit(100)]
