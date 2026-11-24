from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt


class PaymentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_id: StrictInt = Field(gt=0)


class Simulation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result: Literal["APPROVED", "REJECTED"]


class PaymentEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=8, max_length=100)
    payment_id: StrictInt = Field(gt=0)
    amount: StrictInt = Field(gt=0)
    currency: Literal["CLP"]
    status: Literal["APPROVED", "REJECTED"]


class TestCardInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    number: str = Field(min_length=16, max_length=23)
