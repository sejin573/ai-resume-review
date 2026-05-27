from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsageBucket(BaseModel):
    used: int
    limit: int
    remaining: int | None = None
    unlimited: bool = False


class UsageSummaryResponse(BaseModel):
    plan: str
    is_admin: bool
    review_daily: UsageBucket
    refine_daily: UsageBucket
    pdf_monthly: UsageBucket
    periods: dict[str, str]


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None = None
    plan: str = "free"
    is_admin: bool = False
    usage: UsageSummaryResponse | None = None

    class Config:
        from_attributes = True
