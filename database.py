import os
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Table, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import JSONB

# This checks for the DATABASE_URL environment variable.
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set.")

# Add this line to handle SSL connections correctly.
# The sslmode=require parameter is needed for Supabase's enforced SSL.
DATABASE_URL += "?sslmode=require"

Base = declarative_base()

# Define the join table for a many-to-many relationship
group_members_table = Table('group_members', Base.metadata,
    Column('group_id', Integer, ForeignKey('channel_groups.id')),
    Column('channel_id', Integer, ForeignKey('channels.id'))
)

class Channel(Base):
    __tablename__ = 'channels'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    telegram_chat_id = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'))
    channel_owner_contact_id = Column(String)
    is_bot_admin = Column(Boolean, default=False)
    
class Category(Base):
    __tablename__ = 'categories'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

class ChannelGroup(Base):
    __tablename__ = 'channel_groups'
    id = Column(Integer, primary_key=True)
    group_name = Column(String, unique=True, nullable=False)
    ppc_percentage = Column(Numeric, nullable=False)
    channels = relationship("Channel", secondary=group_members_table, backref="channel_groups")

class Campaign(Base):
    __tablename__ = 'campaigns'
    id = Column(Integer, primary_key=True)
    image_file_id = Column(Text, nullable=False)
    text = Column(Text, nullable=False)
    base_url = Column(Text, nullable=False)
    campaign_id = Column(String, unique=True, nullable=False)
    total_campaign_ppc = Column(Numeric, nullable=False)

class Log(Base):
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True)
    action = Column(String, nullable=False)
    details = Column(JSONB)
    timestamp = Column(DateTime, nullable=False)

class CampaignPosting(Base):
    __tablename__ = 'campaign_postings'
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'))
    channel_id = Column(Integer, ForeignKey('channels.id'))
    status = Column(String, nullable=False)
    sent_at = Column(DateTime)
    posted_at = Column(DateTime)
    message_id = Column(Integer) # Added for message deletion

# This creates the database engine.
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
