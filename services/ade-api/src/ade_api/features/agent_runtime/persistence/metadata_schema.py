"""Shared SQLAlchemy metadata identity and scalar types."""

from sqlalchemy import DateTime, MetaData, text
from sqlalchemy.dialects.postgresql import UUID


SCHEMA_NAME = "ade"
METADATA = MetaData(
    schema=SCHEMA_NAME,
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    },
)

UUID_ID = UUID(as_uuid=False)
TIMESTAMP = DateTime(timezone=True)
CREATED_AT = text("CURRENT_TIMESTAMP")
