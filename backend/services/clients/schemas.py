from pydantic import BaseModel, ConfigDict, Field, field_validator, StrictInt


class ClientInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    full_name: str = Field(min_length=2, max_length=150)
    email: str = Field(pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$", max_length=254)
    phone: str = Field(min_length=6, max_length=30)
    address: str = Field(min_length=3, max_length=250)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()
    

class Verification(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class ReceiptMail(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sale_id: StrictInt = Field(gt=0)
    message: str = Field(min_length=1, max_length=30000)
