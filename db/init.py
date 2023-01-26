from db.database import get_db
from db.models import models


def init():
    db = get_db()
    for model in models:
        db.create_table(model)


if __name__ == '__main__':
    init()
