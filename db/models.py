from datetime import datetime

from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Rule(Base):
    __tablename__ = 'rule'

    # whitelist, blacklist, label:<label-name>
    type = Column(String, primary_key=True)

    query = Column(String, primary_key=True)

    apply_to = Column(String, primary_key=True)

    timestamp = Column(DateTime, default=datetime.utcnow)


models = [
    Rule
]
