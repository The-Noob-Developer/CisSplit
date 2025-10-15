# main.py

from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
# Import models, schemas, and the database session dependency
import models, schemas
from database import SessionLocal, engine, get_db
from typing import Dict
from pydantic import ValidationError
# Create all database tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Expense Splitter API")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Expense Splitter API"}

# --- User Endpoints ---
@app.post("/users/", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def create_user(user: dict, db: Session = Depends(get_db)):
    try:
        validated_user = schemas.UserCreate(**user)
    except ValidationError as e:
        error_msg = e.errors()[0]['msg']
        raise HTTPException(status_code=400, detail=error_msg)
    db_user = db.query(models.User).filter(models.User.email.__eq__(validated_user.email)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = models.User(username=validated_user.username, email=validated_user.email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# --- All Users Endpoint ---
@app.get("/users/", response_model=List[schemas.User])
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    return [{"id": u.id, "username": u.username, "email": u.email} for u in users]

@app.get("/groups" , response_model=List[schemas.Group])
def get_all_groups(db: Session = Depends(get_db)):
    groups = db.query(models.Group).all()
    return [{"id" : g.id , "name" : g.name , "members" : g.members} for g in groups]


# --- Group Endpoints ---
@app.post("/groups/", response_model=schemas.Group, status_code=status.HTTP_201_CREATED)
def create_group(group: schemas.GroupCreate, db: Session = Depends(get_db)):
    new_group = models.Group(name=group.name)
    # Find user objects from the provided IDs
    members = db.query(models.User).filter(models.User.id.in_(group.member_ids)).all()
    if len(members) != len(group.member_ids):
        raise HTTPException(status_code=404, detail="One or more user IDs not found")
    new_group.members.extend(members)
    
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    return new_group

# --- Expense Endpoint ---
@app.post("/groups/{group_id}/expenses/", response_model=schemas.Expense, status_code=status.HTTP_201_CREATED)
def create_expense(group_id: int, expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    if not expense.participant_user_ids:
        raise HTTPException(status_code=400, detail="Expense must have at least one participant.")
    
    # Core logic: Calculate the share for each participant
    share_amount = round(expense.amount / len(expense.participant_user_ids), 2)
    
    # Create the main expense record
    new_expense = models.Expense(
        description=expense.description,
        amount=expense.amount,
        group_id=group_id,
        paid_by_user_id=expense.paid_by_user_id
    )
    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)
    
    # Create the participant records with their calculated share
    for user_id in expense.participant_user_ids:
        participant = models.ExpenseParticipant(
            expense_id=new_expense.id,
            user_id=user_id,
            share_amount=share_amount
        )
        db.add(participant)
    
    db.commit()
    return new_expense

# --- User Summary Endpoint ---
@app.get("/users/summary/", response_model=schemas.UserSummary)
def get_user_summary(email: str, db: Session = Depends(get_db)):
    """
    Retrieves a full financial summary for a user based on their email.
    Shows all groups they are a part of and their net balance in each group.
    """
    # Step 1: Find the user by email
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    # Step 2: Find all groups the user is a member of
    user_groups = db.query(models.Group).filter(models.Group.members.any(id=user.id)).all()
    
    group_statuses = []
    
    # Step 3: For each group, calculate the user's financial status
    for group in user_groups:
        # Get all expenses for this group to show in the response
        group_expenses_from_db = db.query(models.Expense).filter(models.Expense.group_id == group.id).all()
        detailed_expenses = [schemas.ExpenseDetail.from_orm(exp) for exp in group_expenses_from_db]
        
        # Calculate the total amount the user has paid for this group's expenses
        total_paid_by_user = db.query(func.sum(models.Expense.amount)).filter(
            models.Expense.group_id == group.id,
            models.Expense.paid_by_user_id == user.id
        ).scalar() or 0.0
        
        # Calculate the user's total share from all expenses in this group
        total_user_share = db.query(func.sum(models.ExpenseParticipant.share_amount)).join(models.Expense).filter(
            models.Expense.group_id == group.id,
            models.ExpenseParticipant.user_id == user.id
        ).scalar() or 0.0
        
        # The net balance is the difference
        net_balance = round(total_paid_by_user - total_user_share, 2)
        
        # Create the status object for this group
        group_status = schemas.GroupStatus(
            group_id=group.id,
            group_name=group.name,
            total_you_paid=round(total_paid_by_user, 2),
            your_total_share=round(total_user_share, 2),
            net_balance=net_balance,
            expenses=detailed_expenses
        )
        group_statuses.append(group_status)

    # Step 4: Assemble the final summary object and return it
    return schemas.UserSummary(
        user_id=user.id,
        username=user.username,
        email=user.email,
        groups=group_statuses
    )


@app.get("/groups/{group_id}/balances/", response_model=Dict[str, float])
def get_group_balances(group_id: int, db: Session = Depends(get_db)):
    """
    Calculates and returns the net balance for every member in a specific group.
    A positive balance means the user is owed money.
    A negative balance means the user owes money.
    """
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    balances = {}
    for member in group.members:
        # Calculate total amount paid by this member in this group
        total_paid = db.query(func.sum(models.Expense.amount)).filter(
            models.Expense.group_id == group_id,
            models.Expense.paid_by_user_id == member.id
        ).scalar() or 0.0

        # Calculate total share for this member in this group
        total_share = db.query(func.sum(models.ExpenseParticipant.share_amount)).join(models.Expense).filter(
            models.Expense.group_id == group_id,
            models.ExpenseParticipant.user_id == member.id
        ).scalar() or 0.0
        
        net_balance = total_paid - total_share
        balances[member.username] = round(net_balance, 2)
        
    return balances