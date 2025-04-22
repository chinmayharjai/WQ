import os
import glob
from bs4 import BeautifulSoup
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

def clean_text(text):
    """Clean and format text for markdown"""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters that might break markdown
    text = re.sub(r'[^\w\s.,!?-]', '', text)
    
    # Ensure proper line breaks
    text = text.replace('. ', '.\n')
    text = text.replace('? ', '?\n')
    text = text.replace('! ', '!\n')
    
    return text.strip()

def extract_media_links(soup, base_url):
    """Extract media links from the HTML content"""
    media_links = {
        'youtube': [],
        'videos': [],
        'images': []
    }
    
    # Extract YouTube links
    youtube_pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]+)'
    
    # Check all links
    for a in soup.find_all('a', href=True):
        href = a['href']
        full_url = urljoin(base_url, href)
        
        # Check for YouTube links
        youtube_match = re.search(youtube_pattern, full_url)
        if youtube_match:
            video_id = youtube_match.group(1)
            media_links['youtube'].append(f"https://www.youtube.com/watch?v={video_id}")
        
        # Check for video links (excluding YouTube)
        elif any(ext in full_url.lower() for ext in ['.mp4', '.webm', '.ogg', '.mov']):
            media_links['videos'].append(full_url)
    
    # Extract image links
    for img in soup.find_all('img', src=True):
        src = img['src']
        full_url = urljoin(base_url, src)
        
        # Check if it's an image URL
        if any(ext in full_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            media_links['images'].append(full_url)
    
    return media_links

def format_media_links(media_links):
    """Format media links for markdown"""
    formatted = []
    
    if media_links['youtube']:
        formatted.append("\n### YouTube Videos")
        for url in media_links['youtube']:
            formatted.append(f"- [Watch on YouTube]({url})")
    
    if media_links['videos']:
        formatted.append("\n### Platform Videos")
        for url in media_links['videos']:
            formatted.append(f"- [Watch Video]({url})")
    
    if media_links['images']:
        formatted.append("\n### Images")
        for url in media_links['images']:
            formatted.append(f"![Image]({url})")
    
    return '\n'.join(formatted)

def extract_relevant_content(html_content, url):
    """Extract relevant content from HTML"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove unwanted elements
    for element in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe', 'noscript']):
        element.decompose()
    
    # Extract main content
    main_content = []
    
    # Extract media links
    media_links = extract_media_links(soup, url)
    
    # Try to find the main content area
    main_areas = soup.find_all(['main', 'article', 'div'], class_=re.compile(r'(content|main|article|post|body)', re.I))
    
    if main_areas:
        for area in main_areas:
            # Extract headings
            for heading in area.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                main_content.append(f"\n{'#' * int(heading.name[1])} {heading.get_text().strip()}\n")
            
            # Extract paragraphs
            for p in area.find_all('p'):
                text = clean_text(p.get_text())
                if text:
                    main_content.append(f"{text}\n")
    else:
        # Fallback: extract all paragraphs if no main content area found
        for p in soup.find_all('p'):
            text = clean_text(p.get_text())
            if text:
                main_content.append(f"{text}\n")
    
    # Add URL as source
    if main_content:
        main_content.insert(0, f"\n## Source: {url}\n")
        
        # Add media links if any exist
        media_section = format_media_links(media_links)
        if media_section.strip():
            main_content.append("\n## Media Content")
            main_content.append(media_section)
    
    return '\n'.join(main_content)

def process_directory(directory):
    """Process all HTML files in a directory"""
    all_content = []
    html_files = glob.glob(os.path.join(directory, "**/*.html"), recursive=True)
    
    print(f"Processing {len(html_files)} files from {directory}...")
    
    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
                
            # Get relative path for URL
            relative_path = os.path.relpath(html_file, directory)
            url = f"file://{relative_path}"
            
            content = extract_relevant_content(html_content, url)
            if content.strip():
                all_content.append(content)
                
        except Exception as e:
            print(f"Error processing {html_file}: {str(e)}")
    
    return all_content

def main():
    # Create output directory if it doesn't exist
    output_dir = "cleaned_content"
    os.makedirs(output_dir, exist_ok=True)
    
    # Process both directories
    platform_content = process_directory("scraped_content")
    support_content = process_directory("scraped_support_content")
    
    # Combine all content
    all_content = []
    
    if platform_content:
        all_content.append("# Platform Content\n")
        all_content.extend(platform_content)
    
    if support_content:
        all_content.append("\n# Support Content\n")
        all_content.extend(support_content)
    
    # Save to markdown file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"combined_content_{timestamp}.md")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_content))
    
    print(f"\nProcessing complete!")
    print(f"Total platform pages processed: {len(platform_content)}")
    print(f"Total support pages processed: {len(support_content)}")
    print(f"Combined content saved to: {output_file}")

if __name__ == "__main__":
    main() 