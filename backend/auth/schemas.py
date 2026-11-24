from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class IntrospectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=1, max_length=512)


class RegistrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=256)


class UserInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    role: Literal["client", "admin"] = "client"
    enabled: bool = True


class UserCreate(UserInput):
    password: str = Field(min_length=8, max_length=256)


class UserUpdate(UserInput):
    password: str | None = Field(default=None, min_length=8, max_length=256)
