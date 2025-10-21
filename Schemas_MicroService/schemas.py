# -*- coding: utf-8 -*-
"""Classes for Request/Response schema definitions."""
# pylint: disable=too-few-public-methods
from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict  # pylint: disable=no-name-in-module

class Message(BaseModel):
    """Message schema definition."""
    detail: Optional[str] = Field(example="error or success message")

class Delivery(BaseModel):
    """Delivery schema definition."""
    model_config = ConfigDict(from_attributes=True)  # ORM mode ON
    
    id: int = Field(
        description="Primary key/identifier of the delivery.",
        default=None,
    )
    order_id: int = Field(
        description="Id of the order that is going to be delivered",
        default=None,
    )
    description: str = Field(
        description="Human readable description for the delivery",
        default="No description",
    )
    date: Optional[datetime] = Field(
        description="Date of the delivery",
        example="2022-07-22T17:32:32.193211"
    )
    status: Literal["delivering", "waiting", "delivered"] = Field(
        description="Current status of the delivery",
        default="delivering",
        example="delivering"
    )
    client_info: Optional[str] = Field(
        description="Client information who received the delivery",
        default=None,
        example="John Doe - DNI: 12345678X"
    )

class DeliveryPost(BaseModel):
    """Delivery creation schema definition."""
    order_id: int = Field(
        description="Id of the order that is going to be delivered",
        example=100,
        gt=0
    )
    description: str = Field(
        description="Human readable description for the delivery",
        default="No description",
        example="Delivery for order #12345"
    )
    date: Optional[datetime] = Field(
        description="Date of the delivery",
        default=None,
        example="2022-07-22T17:32:32.193211"
    )
    status: Literal["delivering", "waiting", "delivered"] = Field(
        description="Status of the order",
        default="delivering"
    )

class DeliveryStatusUpdate(BaseModel):
    """Schema for updating only the delivery status."""
    status: Literal["delivering", "waiting", "delivered"] = Field(
        description="New status of the delivery",
        example="delivered"
    )

class ClientInfo(BaseModel):
    """Client information schema for delivery confirmation."""
    info: str = Field(
        description="Client information (name, signature, ID, etc.)",
        example="John Doe - DNI: 12345678X",
        min_length=1,
        max_length=500
    )