from sqlalchemy import (Column,Integer,BigInteger,String,JSON,Text,ForeignKey,
                        UniqueConstraint)
from sqlalchemy.orm import relationship
from src.config.database import Base
class User(Base):
 __tablename__='users'
 id=Column(Integer,primary_key=True);email=Column(String(100),unique=True,nullable=False);password=Column(String(200));role=Column(String(20))
class Performance(Base):
 __tablename__='performances'
 id=Column(Integer,primary_key=True);code=Column(String(60),unique=True,nullable=False)
 day=Column(String(10));venue=Column(String(40));play=Column(String(60));seats=Column(Integer)
 version=Column(Integer,nullable=False,default=1)
 channels=relationship('SettlementChannel',back_populates='performance',
                       cascade='all, delete-orphan',order_by='SettlementChannel.channel',
                       lazy='selectin')
class SettlementChannel(Base):
 __tablename__='settlement_channels'
 __table_args__=(UniqueConstraint('performance_id','channel',name='uq_performance_channel'),)
 id=Column(Integer,primary_key=True)
 performance_id=Column(Integer,ForeignKey('performances.id',ondelete='CASCADE'),nullable=False,index=True)
 channel=Column(String(30),nullable=False)
 gross_cents=Column(BigInteger);refund_cents=Column(BigInteger);fee_cents=Column(BigInteger);checked=Column(Integer)
 performance=relationship('Performance',back_populates='channels')
class PerformanceRevision(Base):
 __tablename__='performance_revisions'
 id=Column(Integer,primary_key=True)
 performance_id=Column(Integer,ForeignKey('performances.id',ondelete='CASCADE'),nullable=False,index=True)
 version=Column(Integer,nullable=False);action=Column(String(20),nullable=False)
 snapshot=Column(JSON,nullable=False);created=Column(String(40))
 __table_args__=(UniqueConstraint('performance_id','version',name='uq_performance_revision'),)
class SplitDraft(Base):
 __tablename__='split_drafts'
 id=Column(Integer,primary_key=True)
 performance_id=Column(Integer,ForeignKey('performances.id',ondelete='CASCADE'),nullable=False,index=True)
 base_version=Column(Integer,nullable=False);status=Column(String(20),default='draft',nullable=False)
 channels=Column(JSON,nullable=False);note=Column(Text,default='')
 applied_version=Column(Integer,nullable=True);result=Column(JSON,nullable=True)
 created=Column(String(40));updated=Column(String(40))
class Pivot(Base):
 __tablename__='pivots'
 id=Column(Integer,primary_key=True);name=Column(String(100));row_dim=Column(String(30));col_dim=Column(String(30));state=Column(String(20),default='queued');result=Column(JSON,nullable=True);error=Column(Text,default='')
class Review(Base):
 __tablename__='reviews'
 id=Column(Integer,primary_key=True);pivot_id=Column(Integer,ForeignKey('pivots.id'));row_key=Column(String(100));col_key=Column(String(100));book_cents=Column(BigInteger);expected_cents=Column(BigInteger);difference_cents=Column(BigInteger);note=Column(Text);status=Column(String(20),default='draft')
class Audit(Base):
 __tablename__='audits'
 id=Column(Integer,primary_key=True);actor=Column(String(100));action=Column(String(200));created=Column(String(40))
