from pydantic import BaseModel
from typing import Optional


class PortfolioCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    project_url: Optional[str] = None
    business_id: int


class PortfolioUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    project_url: Optional[str] = None
    is_visible: Optional[bool] = None


class PortfolioResponse(BaseModel):
    id: int
    business_id: int
    title: str
    description: Optional[str]
    category: Optional[str]
    image_url: Optional[str]
    project_url: Optional[str]
    is_visible: bool

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    business_id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    contact_url: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    contact_url: Optional[str] = None
    is_visible: Optional[bool] = None


class ProductResponse(ProductCreate):
    id: int
    is_visible: bool

    model_config = {"from_attributes": True}


from pydantic import BaseModel, Field
from typing import Optional


class TestimonialCreate(BaseModel):
    business_id: int
    customer_name: str
    feedback: str
    rating: int = Field(default=5, ge=1, le=5)
    photo_url: Optional[str] = None


class TestimonialUpdate(BaseModel):
    customer_name: Optional[str] = None
    feedback: Optional[str] = None
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    photo_url: Optional[str] = None
    is_visible: Optional[bool] = None


class TestimonialResponse(TestimonialCreate):
    id: int
    is_visible: bool

    model_config = {"from_attributes": True}


from pydantic import BaseModel, EmailStr
from typing import Optional

class EnquiryUpdate(BaseModel):
    status: str

    
class EnquiryCreate(BaseModel):
    business_id: int
    name: str
    email: EmailStr
    phone: Optional[str] = None
    message: str


class EnquiryStatusUpdate(BaseModel):
    status: str


class EnquiryResponse(BaseModel):
    id: int
    business_id: int
    name: str
    email: str
    phone: Optional[str]
    message: str
    status: str

    model_config = {"from_attributes": True}

from pydantic import BaseModel
from typing import Optional


class BusinessCreate(BaseModel):
    name: str
    username: str
    bio: Optional[str] = None
    category: Optional[str] = None
    logo_url: Optional[str] = None
    cover_url: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    social_links: dict = {}
    theme: str = "violet"


class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    category: Optional[str] = None
    logo_url: Optional[str] = None
    cover_url: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    social_links: Optional[dict] = None
    theme: Optional[str] = None
    is_published: Optional[bool] = None


class BusinessResponse(BusinessCreate):
    id: int
    is_published: bool

    model_config = {"from_attributes": True}


from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr

    model_config = {"from_attributes": True}


from pydantic import BaseModel, Field
from typing import Optional


class CheckoutRequest(BaseModel):
    plan_code: str = Field(pattern="^(pro|business)$")


class VerifyPaymentRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_subscription_id: str
    razorpay_signature: str


class CancelSubscriptionRequest(BaseModel):
    cancel_at_cycle_end: bool = True


class SubscriptionResponse(BaseModel):
    plan_code: str
    status: str

    trial_end: Optional[str] = None
    current_start: Optional[str] = None
    current_end: Optional[str] = None

    cancel_at_cycle_end: bool = False
    razorpay_subscription_id: Optional[str] = None


class PaymentHistoryItem(BaseModel):
    razorpay_payment_id: str
    amount: float
    currency: str
    status: str
    created_at: Optional[str] = None