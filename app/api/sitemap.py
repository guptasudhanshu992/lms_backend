from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from datetime import datetime
from ..core.database import get_db
from ..models.blog import Blog
from ..models.course import Course

router = APIRouter(tags=["SEO"])


@router.get("/sitemap.xml", response_class=Response)
async def generate_sitemap(db: Session = Depends(get_db)):
    """Generate XML sitemap for search engines."""
    
    # Get all published blogs
    blogs = db.query(Blog).filter(Blog.is_published == True).all()
    
    # Get all published courses
    courses = db.query(Course).filter(Course.is_published == True).all()
    
    # Base URL - replace with your actual domain
    base_url = "https://yourdomain.com"
    
    # Build sitemap XML
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    # Static pages
    static_pages = [
        {"loc": "/", "priority": "1.0", "changefreq": "daily"},
        {"loc": "/courses", "priority": "0.9", "changefreq": "daily"},
        {"loc": "/blogs", "priority": "0.8", "changefreq": "daily"},
        {"loc": "/about", "priority": "0.7", "changefreq": "weekly"},
        {"loc": "/login", "priority": "0.5", "changefreq": "monthly"},
        {"loc": "/signup", "priority": "0.5", "changefreq": "monthly"},
    ]
    
    for page in static_pages:
        xml_content += f'  <url>\n'
        xml_content += f'    <loc>{base_url}{page["loc"]}</loc>\n'
        xml_content += f'    <changefreq>{page["changefreq"]}</changefreq>\n'
        xml_content += f'    <priority>{page["priority"]}</priority>\n'
        xml_content += f'  </url>\n'
    
    # Blog pages
    for blog in blogs:
        last_mod = blog.updated_at or blog.published_at or blog.created_at
        xml_content += f'  <url>\n'
        xml_content += f'    <loc>{base_url}/blogs/{blog.slug}</loc>\n'
        xml_content += f'    <lastmod>{last_mod.strftime("%Y-%m-%d")}</lastmod>\n'
        xml_content += f'    <changefreq>weekly</changefreq>\n'
        xml_content += f'    <priority>0.7</priority>\n'
        xml_content += f'  </url>\n'
    
    # Course pages
    for course in courses:
        last_mod = course.updated_at or course.created_at
        xml_content += f'  <url>\n'
        xml_content += f'    <loc>{base_url}/courses/{course.slug}</loc>\n'
        xml_content += f'    <lastmod>{last_mod.strftime("%Y-%m-%d")}</lastmod>\n'
        xml_content += f'    <changefreq>weekly</changefreq>\n'
        xml_content += f'    <priority>0.8</priority>\n'
        xml_content += f'  </url>\n'
    
    xml_content += '</urlset>'
    
    return Response(content=xml_content, media_type="application/xml")


@router.get("/rss.xml", response_class=Response)
async def generate_blog_rss(db: Session = Depends(get_db)):
    """Generate RSS feed for blog posts."""
    
    # Get recent published blogs
    blogs = db.query(Blog).filter(
        Blog.is_published == True
    ).order_by(Blog.published_at.desc()).limit(20).all()
    
    base_url = "https://yourdomain.com"
    
    # Build RSS XML
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
    xml_content += '  <channel>\n'
    xml_content += '    <title>LMS Blog - Learning Resources</title>\n'
    xml_content += f'    <link>{base_url}/blogs</link>\n'
    xml_content += '    <description>Latest educational articles, tutorials, and learning resources from our LMS platform.</description>\n'
    xml_content += '    <language>en-us</language>\n'
    xml_content += f'    <lastBuildDate>{datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")}</lastBuildDate>\n'
    xml_content += f'    <atom:link href="{base_url}/rss.xml" rel="self" type="application/rss+xml" />\n'
    
    for blog in blogs:
        pub_date = blog.published_at or blog.created_at
        xml_content += '    <item>\n'
        xml_content += f'      <title>{blog.title}</title>\n'
        xml_content += f'      <link>{base_url}/blogs/{blog.slug}</link>\n'
        xml_content += f'      <guid>{base_url}/blogs/{blog.slug}</guid>\n'
        xml_content += f'      <pubDate>{pub_date.strftime("%a, %d %b %Y %H:%M:%S +0000")}</pubDate>\n'
        if blog.excerpt:
            xml_content += f'      <description><![CDATA[{blog.excerpt}]]></description>\n'
        if blog.author:
            xml_content += f'      <author>{blog.author.email} ({blog.author.full_name})</author>\n'
        xml_content += '    </item>\n'
    
    xml_content += '  </channel>\n'
    xml_content += '</rss>'
    
    return Response(content=xml_content, media_type="application/xml")
