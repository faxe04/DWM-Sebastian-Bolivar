from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator


class OrderItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: StrictInt = Field(gt=0)
    quantity: StrictInt = Field(gt=0, le=100)


class OrderInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[OrderItem] = Field(min_length=1, max_length=50)
    delivery_method: Literal["delivery", "pickup"] = "delivery"

    @model_validator(mode="after")
    def unique_products(self):
        if len({item.product_id for item in self.items}) != len(self.items):
            raise ValueError("No repitas productos")
        return self


class StatusInput(BaseModel):
    status: Literal["PREPARING", "READY", "OUT_FOR_DELIVERY", "DELIVERED"]


class Cancellation(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class PaidInput(BaseModel):
    payment_id: StrictInt = Field(gt=0)
    amount: StrictInt = Field(gt=0)


class SaleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_id: StrictInt = Field(gt=0)
    register_id: StrictInt = Field(default=1, gt=0)
