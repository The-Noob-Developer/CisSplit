# schemas.py

from pydantic import BaseModel, EmailStr
from typing import List

# User Schemas
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    email: EmailStr

class User(UserBase):
    id: int
    class Config:
        from_attributes = True

# Group Schemas
class GroupCreate(BaseModel):
    name: str
    member_ids: List[int]

class Group(BaseModel):
    id: int
    name: str
    members: List[User] = []
    class Config:
        from_attributes = True


# Expense Schemas
class ExpenseCreate(BaseModel):
    description: str
    amount: float
    paid_by_user_id: int
    participant_user_ids: List[int]

class Expense(BaseModel):
    id: int
    description: str
    amount: float
    paid_by_user_id: int
    class Config:
        from_attributes = True

class ExpenseParticipantDetail(BaseModel):
    """Schema for showing participant details within an expense."""
    user_id: int
    share_amount: float

    class Config:
        from_attributes = True

class ExpenseDetail(BaseModel):
    """A detailed schema for an expense, including its participants."""
    id: int
    description: str
    amount: float
    paid_by_user_id: int
    participants: List[ExpenseParticipantDetail] = []

    class Config:
        from_attributes = True

class GroupStatus(BaseModel):
    """Represents the user's financial status within a single group."""
    group_id: int
    group_name: str
    total_you_paid: float
    your_total_share: float
    net_balance: float  # Positive means you are owed, negative means you owe
    expenses: List[ExpenseDetail] = []

class UserSummary(BaseModel):
    """The main response model for the user's complete summary."""
    user_id: int
    username: str
    email: EmailStr
    groups: List[GroupStatus] = []