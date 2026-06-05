import enum

from sqlalchemy import String, LargeBinary, Enum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class AccountStatus(str, enum.Enum):
    ENABLED = 'enabled'
    DISABLED = 'disabled'
    UNVERIFIED = 'unverified'

class Account(Base):
    __tablename__ = 'accounts'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mail: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=True)
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, name='account_status'),
        default=AccountStatus.UNVERIFIED
    )
