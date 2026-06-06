import enum
import datetime
from datetime import datetime as dt

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, LargeBinary, Enum, ForeignKey, DateTime, Integer, Double, func

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
        Enum(
            AccountStatus,
            name='account_status',
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        default=AccountStatus.UNVERIFIED,
    )

    predictions: Mapped[list['Prediction']] = relationship(
        back_populates='account',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )

class Prediction(Base):
    __tablename__ = 'predictions'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    account_id: Mapped[int] = mapped_column(
        ForeignKey('accounts.id', ondelete='CASCADE'),
        nullable=False,
    )

    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rna_sequence: Mapped[str] = mapped_column(String(1024), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    account: Mapped[Account] = relationship(back_populates='predictions')

    coordinates: Mapped[list['PredictionCoordinate']] = relationship(
        back_populates='prediction',
        cascade='all, delete-orphan',
    )

class PredictionCoordinate(Base):
    __tablename__ = 'prediction_coordinates'

    prediction_id: Mapped[int] = mapped_column(
        ForeignKey('predictions.id', ondelete='CASCADE'),
        primary_key=True,
    )

    position: Mapped[int] = mapped_column(Integer, primary_key=True)

    x: Mapped[float] = mapped_column(Double, nullable=False)
    y: Mapped[float] = mapped_column(Double, nullable=False)
    z: Mapped[float] = mapped_column(Double, nullable=False)

    prediction: Mapped[Prediction] = relationship(back_populates='coordinates')
