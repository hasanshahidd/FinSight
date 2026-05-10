"""Pydantic schemas for users + accounts."""

from pydantic import BaseModel


class AccountOut(BaseModel):
    id: str
    name: str
    type: str
    starting_balance: float
    currency: str = "USD"

    class Config:
        from_attributes = True


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    persona: str
    description: str

    class Config:
        from_attributes = True


class UserWithAccounts(UserOut):
    accounts: list[AccountOut]
