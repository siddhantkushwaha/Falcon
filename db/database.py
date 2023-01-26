import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from params import root_dir


def get_db(name='db'):
    db_path = os.path.join(root_dir, 'data', f'{name}.sqlite')
    engine_url = 'sqlite:///' + db_path
    db = Database(engine_url)
    return db


class Database:

    def __init__(self, engine_url):
        self.engine_ = create_engine(engine_url)
        self.session_ = sessionmaker(bind=self.engine, expire_on_commit=False)()

    def __del__(self):
        self.session.expunge_all()
        self.session.close()

    @property
    def engine(self):
        return self.engine_

    @property
    def session(self):
        return self.session_

    def create_table(self, model):
        try:
            model.__table__.create(bind=self.engine)
        except Exception as exp:
            return exp

        return True

    def drop_table(self, model):
        try:
            model.__table__.drop(bind=self.engine)
        except Exception as exp:
            return exp

        return True
