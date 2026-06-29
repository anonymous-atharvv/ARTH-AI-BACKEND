# backend/models/transaction_embedding.py
from sqlalchemy import Column, Float, Text, String, JSON
from database import Base
from models.user import GUID

class TransactionEmbedding(Base):
    __tablename__ = "transaction_embeddings"

    transaction_id = Column(GUID(), primary_key=True)
    embedding = Column(JSON, nullable=False)  # Stores list of floats (embedding vector)
    description_normalized = Column(Text, nullable=False)
    category_code = Column(String(100), nullable=False)
    confidence = Column(Float, default=1.0)
