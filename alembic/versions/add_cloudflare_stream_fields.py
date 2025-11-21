"""Add Cloudflare Stream fields to lessons table

Revision ID: add_cloudflare_stream
Revises: previous_revision
Create Date: 2025-11-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_cloudflare_stream'
down_revision = None  # Update this with your previous migration ID
branch_labels = None
depends_on = None


def upgrade():
    # Add Cloudflare Stream columns to lessons table
    op.add_column('lessons', sa.Column('cloudflare_stream_id', sa.String(255), nullable=True))
    op.add_column('lessons', sa.Column('cloudflare_video_uid', sa.String(255), nullable=True))
    op.add_column('lessons', sa.Column('video_status', sa.String(50), nullable=True))
    op.add_column('lessons', sa.Column('thumbnail_url', sa.String(500), nullable=True))
    op.add_column('lessons', sa.Column('video_duration_seconds', sa.Integer(), nullable=True))
    
    # Create index on cloudflare_stream_id for faster lookups
    op.create_index('ix_lessons_cloudflare_stream_id', 'lessons', ['cloudflare_stream_id'])


def downgrade():
    # Remove index
    op.drop_index('ix_lessons_cloudflare_stream_id', table_name='lessons')
    
    # Remove columns
    op.drop_column('lessons', 'video_duration_seconds')
    op.drop_column('lessons', 'thumbnail_url')
    op.drop_column('lessons', 'video_status')
    op.drop_column('lessons', 'cloudflare_video_uid')
    op.drop_column('lessons', 'cloudflare_stream_id')
