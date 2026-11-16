import random
from datetime import date,timedelta
from src.config.database import Base,engine,Session
from src.models.entities import User,Performance,SettlementChannel
from src.utils.security import hash_password
from src.constants.enums import VENUES,CHANNELS
def seed():
 Base.metadata.create_all(engine);rng=random.Random(3112)
 with Session() as s:
  for role in ('admin','analyst','viewer'):
   email=role+'@demo.local'
   if not s.query(User).filter_by(email=email).first():s.add(User(email=email,role=role,password=hash_password('Demo123!')))
  existing={code for (code,) in s.query(Performance.code).all()}
  for i in range(180):
   code=f'YM-{i+1:03}'
   if code in existing:continue
   seats=[800,240,120][i%3];checked=rng.randint(seats//2,seats);gross=checked*rng.choice([8000,12000,18000])
   refund=rng.randint(0,checked//10)*8000;fee=int((gross-refund)*[0,.07,.03][i%3]);channel=CHANNELS[(i//3)%3]
   p=Performance(code=code,day=(date(2026,9,1)+timedelta(days=i//3)).isoformat(),venue=VENUES[i%3],
                 play=['渡口来信','星河漫游','一间书房','冬日序曲'][i%4],seats=seats,version=1)
   p.channels=[SettlementChannel(channel=channel,gross_cents=gross,refund_cents=refund,fee_cents=fee,checked=checked)]
   s.add(p)
  s.commit();print({'users':s.query(User).count(),'performances':s.query(Performance).count(),
                   'channels':s.query(SettlementChannel).count()})
if __name__=='__main__':seed()
