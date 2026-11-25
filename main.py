from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session
from database import get_db
from models import PortfolioProject
from schemas import PortfolioCreate, PortfolioUpdate, PortfolioResponse
from models import Product
from schemas import ProductCreate, ProductUpdate, ProductResponse
from models import Testimonial
from models import PageView
from models import RevokedToken
from schemas import (
    TestimonialCreate,
    TestimonialUpdate,
    TestimonialResponse
)
from models import Enquiry
from schemas import (
    EnquiryCreate,
    EnquiryStatusUpdate,
    EnquiryResponse
)
import os
import jwt
from fastapi import UploadFile, File
from cloudinary_service import upload_image

from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash

from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session

from models import User
from schemas import RegisterRequest, LoginRequest, UserResponse
from models import Business, PortfolioProject, Product, Testimonial

from schemas import (
    BusinessResponse,
    PortfolioResponse,
    ProductResponse,
    TestimonialResponse
)
from models import Business
from schemas import BusinessCreate, BusinessUpdate, BusinessResponse
from database import engine, Base, get_db
from fastapi import HTTPException
from security import get_current_user
from models import User
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from database import get_db
from models import Product, Testimonial, Enquiry, Business, User
from schemas import (
    ProductCreate, ProductUpdate,
    TestimonialCreate, TestimonialUpdate,
    EnquiryCreate, EnquiryUpdate
)
from fastapi import UploadFile, File
from cloudinary_service import upload_image
from security import get_current_user
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()
app = FastAPI(
    title="Proofly API",
    description="Backend API for the Proofly platform",
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://proofly-page.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Create database tables when models are added
Base.metadata.create_all(bind=engine)
password_hash = PasswordHash.recommended()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


@app.get("/")
def home():
    return {
        "message": "Welcome to Proofly API"
    }


@app.get("/api/v1/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected"
    }

@app.post("/api/v1/uploads/image")
def upload_image_endpoint(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Please upload an image file"
        )

    try:
        result = upload_image(file.file)
        return result

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Image upload failed"
        )

@app.post("/api/v1/portfolio", response_model=PortfolioResponse)
def create_portfolio(
    data: PortfolioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_owned_business(
        db,
        data.business_id,
        current_user.id
    )

    project = PortfolioProject(**data.model_dump())

    db.add(project)
    db.commit()
    db.refresh(project)

    return project


@app.get("/api/v1/portfolio", response_model=list[PortfolioResponse])
def get_portfolio(
    business_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_owned_business(
        db,
        business_id,
        current_user.id
    )

    return db.query(PortfolioProject).filter(
        PortfolioProject.business_id == business_id
    ).all()

@app.get(
    "/api/v1/portfolio/{project_id}",
    response_model=PortfolioResponse
)
def get_portfolio_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = get_owned_item(
        db,
        PortfolioProject,
        project_id,
        current_user.id
    )

    return project


@app.put(
    "/api/v1/portfolio/{project_id}",
    response_model=PortfolioResponse
)
def update_portfolio(
    project_id: int,
    data: PortfolioUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = get_owned_item(
        db,
        PortfolioProject,
        project_id,
        current_user.id
    )

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)

    return project


@app.delete("/api/v1/portfolio/{project_id}")
def delete_portfolio(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = get_owned_item(
        db,
        PortfolioProject,
        project_id,
        current_user.id
    )

    db.delete(project)
    db.commit()

    return {"message": "Portfolio project deleted"}

@app.post("/api/v1/products")
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_owned_business(db, data.business_id, current_user.id)

    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.get("/api/v1/products")
def get_products(
    business_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_owned_business(db, business_id, current_user.id)

    return db.query(Product).filter(
        Product.business_id == business_id
    ).all()


@app.get("/api/v1/products/{product_id}")
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return get_owned_item(db, Product, product_id, current_user.id)


@app.put("/api/v1/products/{product_id}")
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    product = get_owned_item(
        db, Product, product_id, current_user.id
    )

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product


@app.delete("/api/v1/products/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    product = get_owned_item(
        db, Product, product_id, current_user.id
    )

    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}


@app.post("/api/v1/testimonials")
def create_testimonial(
    data: TestimonialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_owned_business(db, data.business_id, current_user.id)

    testimonial = Testimonial(**data.model_dump())
    db.add(testimonial)
    db.commit()
    db.refresh(testimonial)
    return testimonial


@app.get("/api/v1/testimonials")
def get_testimonials(
    business_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_owned_business(db, business_id, current_user.id)

    return db.query(Testimonial).filter(
        Testimonial.business_id == business_id
    ).all()

@app.put("/api/v1/testimonials/{testimonial_id}")
def update_testimonial(
    testimonial_id: int,
    data: TestimonialUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    testimonial = get_owned_item(
        db, Testimonial, testimonial_id, current_user.id
    )

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(testimonial, key, value)

    db.commit()
    db.refresh(testimonial)
    return testimonial



@app.delete("/api/v1/testimonials/{testimonial_id}")
def delete_testimonial(
    testimonial_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    testimonial = get_owned_item(
        db, Testimonial, testimonial_id, current_user.id
    )

    db.delete(testimonial)
    db.commit()
    return {"message": "Testimonial deleted successfully"}

@app.post("/api/v1/enquiries")
def create_enquiry(
    data: EnquiryCreate,
    db: Session = Depends(get_db)
):
    business = db.query(Business).filter(
        Business.id == data.business_id,
        Business.is_published == True
    ).first()

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )

    enquiry = Enquiry(**data.model_dump())
    db.add(enquiry)
    db.commit()
    db.refresh(enquiry)
    return enquiry

@app.get("/api/v1/enquiries")
def get_enquiries(
    business_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_owned_business(db, business_id, current_user.id)

    return db.query(Enquiry).filter(
        Enquiry.business_id == business_id
    ).order_by(Enquiry.id.desc()).all()

@app.patch("/api/v1/enquiries/{enquiry_id}")
def update_enquiry(
    enquiry_id: int,
    data: EnquiryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    enquiry = get_owned_item(
        db, Enquiry, enquiry_id, current_user.id
    )

    enquiry.status = data.status

    db.commit()
    db.refresh(enquiry)
    return enquiry

@app.delete("/api/v1/enquiries/{enquiry_id}")
def delete_enquiry(
    enquiry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    enquiry = get_owned_item(
        db, Enquiry, enquiry_id, current_user.id
    )

    db.delete(enquiry)
    db.commit()
    return {"message": "Enquiry deleted successfully"}

@app.post("/api/v1/business", response_model=BusinessResponse)
def create_business(
    data: BusinessCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = db.query(Business).filter(
        Business.username == data.username
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Username already taken"
        )

    business = Business(
        **data.model_dump(),
        user_id=current_user.id
    )

    db.add(business)
    db.commit()
    db.refresh(business)

    return business


@app.get("/api/v1/business/{business_id}", response_model=BusinessResponse)
def get_business(
    business_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    business = get_owned_business(
        db,
        business_id,
        current_user.id
    )

    return business

@app.put("/api/v1/business/{business_id}", response_model=BusinessResponse)
def update_business(
    business_id: int,
    data: BusinessUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    business = get_owned_business(
        db,
        business_id,
        current_user.id
    )

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(business, key, value)

    db.commit()
    db.refresh(business)

    return business

@app.get("/api/v1/business/check-username/{username}")
def check_username(
    username: str,
    db: Session = Depends(get_db)
):
    exists = db.query(Business).filter(
        Business.username == username
    ).first()

    return {"available": exists is None}

@app.get("/api/v1/pages/{username}")
def get_public_page(
    username: str,
    db: Session = Depends(get_db)
):
    business = db.query(Business).filter(
        Business.username == username,
        Business.is_published == True
    ).first()

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Page not found"
        )

    view = PageView(business_id=business.id)
    db.add(view)
    db.commit()

    portfolio = db.query(PortfolioProject).filter(
        PortfolioProject.business_id == business.id,
        PortfolioProject.is_visible == True
    ).all()

    products = db.query(Product).filter(
        Product.business_id == business.id,
        Product.is_visible == True
    ).all()

    testimonials = db.query(Testimonial).filter(
        Testimonial.business_id == business.id,
        Testimonial.is_visible == True
    ).all()

    return {
        "business": BusinessResponse.model_validate(business),
        "portfolio": [
            PortfolioResponse.model_validate(item)
            for item in portfolio
        ],
        "products": [
            ProductResponse.model_validate(item)
            for item in products
        ],
        "testimonials": [
            TestimonialResponse.model_validate(item)
            for item in testimonials
        ]
    }

from sqlalchemy import func
from models import (
    Business,
    PortfolioProject,
    Product,
    Testimonial,
    Enquiry,
    PageView
)


@app.get("/api/v1/dashboard")
def get_dashboard(
    business_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == current_user.id
    ).first()

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )

    portfolio_count = db.query(func.count(PortfolioProject.id)).filter(
        PortfolioProject.business_id == business_id
    ).scalar()

    product_count = db.query(func.count(Product.id)).filter(
        Product.business_id == business_id
    ).scalar()

    testimonial_count = db.query(func.count(Testimonial.id)).filter(
        Testimonial.business_id == business_id
    ).scalar()

    enquiry_count = db.query(func.count(Enquiry.id)).filter(
        Enquiry.business_id == business_id
    ).scalar()

    page_view_count = db.query(func.count(PageView.id)).filter(
        PageView.business_id == business_id
    ).scalar()

    return {
        "business_name": business.name,
        "username": business.username,
        "is_published": business.is_published,
        "total_portfolio": portfolio_count,
        "total_products": product_count,
        "total_testimonials": testimonial_count,
        "total_enquiries": enquiry_count,
        "total_page_views": page_view_count
    }




def create_access_token(user_id: int):
    expire = datetime.now(timezone.utc) + timedelta(days=7)

    payload = {
        "sub": str(user_id),
        "exp": expire
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )


@app.post("/api/v1/auth/register")
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(
        User.email == data.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    user = User(
        name=data.name,
        email=data.email,
        hashed_password=password_hash.hash(data.password)
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }


@app.post("/api/v1/auth/login")
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == data.email
    ).first()

    if not user or not password_hash.verify(
        data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    token = create_access_token(user.id)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }

@app.post("/api/v1/auth/logout")
def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    token = credentials.credentials

    revoked_token = RevokedToken(token=token)

    db.add(revoked_token)
    db.commit()

    return {
        "message": "Successfully logged out"
    }

def get_owned_business(
    db: Session,
    business_id: int,
    user_id: int
):
    business = db.query(Business).filter(
        Business.id == business_id,
        Business.user_id == user_id
    ).first()

    if not business:
        raise HTTPException(
            status_code=404,
            detail="Business not found"
        )

    return business


def get_owned_item(
    db: Session,
    model,
    item_id: int,
    user_id: int
):
    item = db.query(model).filter(
        model.id == item_id
    ).first()

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Record not found"
        )

    get_owned_business(
        db,
        item.business_id,
        user_id
    )

    return item