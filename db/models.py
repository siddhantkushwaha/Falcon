from sqlalchemy import Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Rule(Base):
    __tablename__ = "rule"

    id = Column(Integer, primary_key=True)

    # whitelist, blacklist, label:<label-name>
    type = Column(String)

    # email:<email> | label:<label-name>
    query = Column(String)

    apply_to = Column(String)

    order = Column(Integer, default=0)

    args = Column(String)


models = [Rule]
