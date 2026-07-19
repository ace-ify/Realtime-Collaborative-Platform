from datetime import datetime
from sqlalchemy import Column, Integer, String, LargeBinary, DateTime
from app.database import Base

class DocumentUpdate(Base):
    __tablename__ = "document_updates"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, index=True, nullable=False)
    
    # LargeBinary represents BLOB datatype to store Yjs binary bytes
    update_data = Column(LargeBinary, nullable=False)
    
    # We use datetime.utcnow to get GMT/UTC timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

class DocumentSnapshot(Base):
    __tablename__ = "document_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String, index=True, nullable=False)
    
    # Stores the full YDoc composite state snapshot bytes
    snapshot_data = Column(LargeBinary, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
