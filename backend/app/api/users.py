"""User + account endpoints — drives the persona switcher."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import current_user
from app.db.models import Account, User
from app.db.session import get_session
from app.schemas.user import AccountOut, UserOut, UserWithAccounts

router = APIRouter()


@router.get("", response_model=list[UserOut])
async def list_users(session: AsyncSession = Depends(get_session)) -> list[UserOut]:
    rows = (await session.execute(select(User))).scalars().all()
    return [UserOut.model_validate(r) for r in rows]


@router.get("/me", response_model=UserWithAccounts)
async def me(
    user_id: str = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> UserWithAccounts:
    q = select(User).where(User.id == user_id).options(selectinload(User.accounts))
    user = (await session.execute(q)).scalars().first()
    if not user:
        raise HTTPException(404, f"user {user_id} not found")
    return UserWithAccounts(
        id=user.id, email=user.email, name=user.name,
        persona=user.persona, description=user.description,
        accounts=[AccountOut.model_validate(a) for a in user.accounts],
    )


@router.get("/{user_id}/accounts", response_model=list[AccountOut])
async def list_accounts(user_id: str, session: AsyncSession = Depends(get_session)) -> list[AccountOut]:
    rows = (await session.execute(select(Account).where(Account.user_id == user_id))).scalars().all()
    return [AccountOut.model_validate(r) for r in rows]
