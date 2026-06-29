# backend/models/category.py
from sqlalchemy import Column, String, Integer
from database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(50), unique=True, nullable=False)
    name_en = Column(String(100), nullable=False)
    name_hi = Column(String(100), nullable=False)
    type = Column(String(10), nullable=False)  # income | expense | transfer
    parent_code = Column(String(50))
    icon = Column(String(10), default="💰")
    sort_order = Column(Integer, default=0)
