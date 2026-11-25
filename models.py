from sqlalchemy import Column, Integer, String, Text, Boolean
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class PortfolioProject(Base):
    __tablename__ = "portfolio_projects"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, nullable=False, index=True)

    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    image_url = Column(String(500), nullable=True)
    project_url = Column(String(500), nullable=True)

    is_visible = Column(Boolean, default=True)


from sqlalchemy import Float


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, nullable=False, index=True)

    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    price = Column(Float, nullable=True)
    image_url = Column(String(500), nullable=True)
    contact_url = Column(String(500), nullable=True)

    is_visible = Column(Boolean, default=True)


class Testimonial(Base):
    __tablename__ = "testimonials"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, nullable=False, index=True)

    customer_name = Column(String(150), nullable=False)
    feedback = Column(Text, nullable=False)
    rating = Column(Integer, default=5)
    photo_url = Column(String(500), nullable=True)

    is_visible = Column(Boolean, default=True)

class Enquiry(Base):
    __tablename__ = "enquiries"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, nullable=False, index=True)

    name = Column(String(150), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(30), nullable=True)
    message = Column(Text, nullable=False)

    status = Column(String(20), default="new")


from sqlalchemy import JSON


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer,ForeignKey("users.id"),nullable=True,index=True)

    name = Column(String(150), nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)

    bio = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)

    logo_url = Column(String(500), nullable=True)
    cover_url = Column(String(500), nullable=True)

    email = Column(String(255), nullable=True)
    phone = Column(String(30), nullable=True)
    address = Column(String(255), nullable=True)

    social_links = Column(JSON, default=dict)
    theme = Column(String(50), default="violet")

    is_published = Column(Boolean, default=False)

from sqlalchemy import DateTime
from sqlalchemy.sql import func


class PageView(Base):
    __tablename__ = "page_views"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, nullable=False, index=True)

    viewed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

from sqlalchemy import DateTime
from sqlalchemy.sql import func


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )