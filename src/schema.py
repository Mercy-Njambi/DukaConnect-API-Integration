from pydantic import BaseModel, Field
from typing import List

class Product(BaseModel):
    product_id: int
    name: str
    price : float
    description : str
    
class ProductCreate(BaseModel):
    name: str = Field(default=..., min_length=2, json_schema_extra={"error_messages": {"required": "Name is missing"}})
    price: float = Field(default=..., gt=0, json_schema_extra={"error_messages": {"required": "Must be a valid number, geater than zero"}})
    description: str = Field(default=..., min_length=10, max_length=500)
    
class OrderItem(BaseModel):
    product_id: int
    quantity: int = Field(default=..., gt=0)
    
class OrderCreate(BaseModel):
    items: List[OrderItem]
    
class Order(BaseModel):
    id: int
    items: List[OrderItem]
    total_amount:float
    
class DescriptionRequest(BaseModel):
    product_name:str
    keywords : list[str]

class PaymentRequest(BaseModel):
    phone_number: str
    order_id : int