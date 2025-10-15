# models.py

from sqlalchemy import Column, Integer, String, Float, ForeignKey, Table
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import List
from database import Base

# Association table for the many-to-many relationship between users and groups
# This definition remains the same as it's standard SQLAlchemy Core.
group_members_table = Table('group_members', Base.metadata,
    Column('group_id', Integer, ForeignKey('groups.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
)

class User(Base):
    __tablename__ = "users"

    # Modern syntax with type hints
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

class Group(Base):
    __tablename__ = "groups"

    # Modern syntax with type hints
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Relationship now includes a Mapped hint for better type checking
    members: Mapped[List["User"]] = relationship(secondary=group_members_table)

class Expense(Base):
    __tablename__ = "expenses"

    # Modern syntax with type hints
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    paid_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    # Relationship to participants with type hint
    participants: Mapped[List["ExpenseParticipant"]] = relationship(back_populates="expense")

class ExpenseParticipant(Base):
    __tablename__ = "expense_participants"
    
    # Modern syntax for composite primary key
    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    share_amount: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Relationship back to the expense with type hint
    expense: Mapped["Expense"] = relationship(back_populates="participants")

