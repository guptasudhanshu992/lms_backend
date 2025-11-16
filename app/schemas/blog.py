from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import re


class BlogBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    excerpt: Optional[str] = Field(None, max_length=500)
    featured_image: Optional[str] = None
    is_published: bool = False
    scheduled_publish_at: Optional[datetime] = None


class BlogCreate(BlogBase):
    @validator('title')
    def validate_title(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()


class BlogUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    excerpt: Optional[str] = Field(None, max_length=500)
    featured_image: Optional[str] = None
    is_published: Optional[bool] = None
    scheduled_publish_at: Optional[datetime] = None


class BlogAuthor(BaseModel):
    id: int
    full_name: Optional[str]
    email: str
    
    class Config:
        from_attributes = True


class BlogResponse(BlogBase):
    id: int
    slug: str
    author_id: int
    published_at: Optional[datetime]
    scheduled_publish_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class BlogWithAuthor(BlogResponse):
    author: BlogAuthor
    
    class Config:
        from_attributes = True


class BlogListResponse(BaseModel):
    blogs: list[BlogWithAuthor]
    total: int
    page: int
    page_size: int
    total_pages: int
