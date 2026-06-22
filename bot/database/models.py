from datetime import datetime

from peewee import (
    BigIntegerField,
    BooleanField,
    CharField,
    DateTimeField,
    IntegerField,
    Model,
    SqliteDatabase,
)

db = SqliteDatabase(None)  # initialised in db.py


class BaseModel(Model):
    class Meta:
        database = db


class User(BaseModel):
    tg_id = BigIntegerField(unique=True)
    username = CharField(null=True)
    full_name = CharField()
    joined_at = DateTimeField(default=datetime.now)
    search_count = IntegerField(default=0)
    dl_count = IntegerField(default=0)
    is_banned = BooleanField(default=False)


class Proxy(BaseModel):
    host = CharField()
    port = IntegerField()
    login = CharField(null=True)
    password = CharField(null=True)
    protocol = CharField(default="http")
    is_active = BooleanField(default=True)
    fail_count = IntegerField(default=0)
    added_at = DateTimeField(default=datetime.now)
    last_used = DateTimeField(null=True)

    def to_url(self) -> str:
        if self.login and self.password:
            return f"{self.protocol}://{self.login}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"
