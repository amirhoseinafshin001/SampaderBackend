# from sqlalchemy import ForeignKey, String, Column, delete
# import db.constants as const


# class Block(const.Base):
#     __tablename__ = "blocks"
#     blockID = Column("blockID", String, primary_key=True, default=const.generate_uuid)
#     blockerID = Column("blocker", String, ForeignKey("users.userID"))
#     blockedID = Column("blocked", String, ForeignKey("users.userID"))
     
#     def __init__(self, blocker, blocked):        
#         self.blockerID = blocker
#         self.blockedID = blocked


# def is_blocked(blocker, blocked):
#     # did blocker user blocked this guy?
#     try:
#         exist = len(
#             const.session.query(Block)
#                 .filter(Block.blockedID == blocked, Block.blockerID == blocker)
#                 .all()
#             ) > 0
#         return exist
#     except:
#         return False


# def block(blocker, blocked_user):
#     # blocking someone:
#     #    add a record to blocks table
#     if not is_blocked(blocker, blocked_user):
#         b = Block(blocker, blocked_user)
#         const.session.add(b)
#         const.session.commit()
#         return True
#     return False


# def unblock(blocker, blocked_user):
#     # unblocking someone:
#     #    remove a record from blocks table
#     if is_blocked(blocker, blocked_user):
#         query = delete(Block).where(Block.blockedID == blocked_user, Block.blockerID == blocker)
#         const.session.execute(query)
#         return True
#     return False


from sqlalchemy import Table, Column, String, ForeignKey
from sqlalchemy.orm import relationship
from db.constants import Base

# Association table for the many-to-many self-referencing relationship
blocks_table = Table(
    'block',
    Base.metadata,
    Column('blocker_id', String, ForeignKey('users.userID'), primary_key=True),
    Column('blocked_id', String, ForeignKey('users.userID'), primary_key=True)
)