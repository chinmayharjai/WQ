import os
import glob
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import markdown2
from bs4 import BeautifulSoup
import re
import requests
from io import BytesIO
from urllib.parse import urlparse

# Use system fonts instead of DejaVu Sans
styles = getSampleStyleSheet()

# Custom styles
styles.add(ParagraphStyle(
    name='CustomTitle',
    parent=styles['Heading1'],
    fontSize=24,
    spaceAfter=30,
    alignment=1
))
styles.add(ParagraphStyle(
    name='CustomHeading',
    parent=styles['Heading2'],
    fontSize=18,
    spaceAfter=20
))
styles.add(ParagraphStyle(
    name='CustomSubHeading',
    parent=styles['Heading3'],
    fontSize=14,
    spaceAfter=15
))
styles.add(ParagraphStyle(
    name='CustomBody',
    parent=styles['Normal'],
    fontSize=12,
    spaceAfter=12
))
styles.add(ParagraphStyle(
    name='CustomLink',
    parent=styles['Normal'],
    fontSize=10,
    textColor=colors.blue,
    spaceAfter=8
))

def clean_text(text):
    """Clean text for PDF formatting"""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def process_markdown_file(markdown_file):
    """Process a markdown file and return formatted content"""
    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Convert markdown to HTML
    html = markdown2.markdown(content)
    soup = BeautifulSoup(html, 'html.parser')
    
    return soup

def download_image(url):
    """Download image from URL and return BytesIO object"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return BytesIO(response.content)
        return None
    except:
        return None

def create_pdf_content(soup, doc):
    """Create PDF content from BeautifulSoup object"""
    elements = []
    
    # Process headings
    for heading in soup.find_all(['h1', 'h2', 'h3']):
        level = int(heading.name[1])
        text = clean_text(heading.get_text())
        
        if level == 1:
            style = 'CustomTitle'
        elif level == 2:
            style = 'CustomHeading'
        else:
            style = 'CustomSubHeading'
        
        elements.append(Paragraph(text, styles[style]))
        elements.append(Spacer(1, 0.2 * inch))
    
    # Process paragraphs
    for p in soup.find_all('p'):
        text = clean_text(p.get_text())
        if text:
            elements.append(Paragraph(text, styles['CustomBody']))
            elements.append(Spacer(1, 0.1 * inch))
    
    # Process links
    for a in soup.find_all('a'):
        href = a.get('href', '')
        text = clean_text(a.get_text())
        if text and href:
            elements.append(Paragraph(f"{text}: {href}", styles['CustomLink']))
    
    # Process images
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if src:
            try:
                # Download image
                image_data = download_image(src)
                if image_data:
                    # Add image with caption
                    elements.append(Image(image_data, width=6*inch, height=4*inch))
                    alt = img.get('alt', '')
                    if alt:
                        elements.append(Paragraph(alt, styles['CustomBody']))
                    elements.append(Spacer(1, 0.2 * inch))
                else:
                    print(f"Skipping image that couldn't be downloaded: {src}")
            except Exception as e:
                print(f"Error processing image {src}: {str(e)}")
                continue
    
    return elements

def main():
    # Create output directory if it doesn't exist
    output_dir = "pdf_content"
    os.makedirs(output_dir, exist_ok=True)
    
    # Get all markdown files
    markdown_files = glob.glob(os.path.join("cleaned_content", "*.md"))
    
    if not markdown_files:
        print("No markdown files found in cleaned_content directory!")
        return
    
    # Create PDF document
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"combined_content_{timestamp}.pdf")
    doc = SimpleDocTemplate(
        output_file,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Create story (content) for PDF
    story = []
    
    # Add title page
    story.append(Paragraph("WorldQuant Brain Content", styles['CustomTitle']))
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['CustomBody']))
    story.append(Spacer(1, 1 * inch))
    
    # Process each markdown file
    for md_file in markdown_files:
        print(f"Processing {md_file}...")
        
        # Add section header
        section_name = os.path.basename(md_file).replace('.md', '')
        story.append(Paragraph(section_name, styles['CustomHeading']))
        story.append(Spacer(1, 0.2 * inch))
        
        # Process content
        soup = process_markdown_file(md_file)
        story.extend(create_pdf_content(soup, doc))
        
        # Add page break between sections
        story.append(Spacer(1, 0.5 * inch))
    
    # Build PDF
    doc.build(story)
    
    print(f"\nPDF generation complete!")
    print(f"Output saved to: {output_file}")

if __name__ == "__main__":
    main() 