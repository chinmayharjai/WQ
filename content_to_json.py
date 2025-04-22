import os
import glob
import json
from bs4 import BeautifulSoup
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

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
            media_links['youtube'].append({
                'url': f"https://www.youtube.com/watch?v={video_id}",
                'title': a.get_text().strip() or f"YouTube Video {video_id}"
            })
        
        # Check for video links (excluding YouTube)
        elif any(ext in full_url.lower() for ext in ['.mp4', '.webm', '.ogg', '.mov']):
            media_links['videos'].append({
                'url': full_url,
                'title': a.get_text().strip() or os.path.basename(full_url)
            })
    
    # Extract image links
    for img in soup.find_all('img', src=True):
        src = img['src']
        full_url = urljoin(base_url, src)
        
        # Check if it's an image URL
        if any(ext in full_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            media_links['images'].append({
                'url': full_url,
                'alt': img.get('alt', ''),
                'title': img.get('title', os.path.basename(full_url))
            })
    
    return media_links

def extract_text_content(soup):
    """Extract and clean text content from HTML"""
    # Remove unwanted elements
    for element in soup(['script', 'style', 'nav', 'footer', 'header', 'iframe', 'noscript']):
        element.decompose()
    
    content = {
        'headings': [],
        'paragraphs': [],
        'links': []
    }
    
    # Extract headings
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        content['headings'].append({
            'level': int(heading.name[1]),
            'text': heading.get_text().strip()
        })
    
    # Extract paragraphs
    for p in soup.find_all('p'):
        text = p.get_text().strip()
        if text:
            content['paragraphs'].append(text)
    
    # Extract regular links (excluding media links)
    for a in soup.find_all('a', href=True):
        href = a['href']
        text = a.get_text().strip()
        if text and not any(ext in href.lower() for ext in ['.mp4', '.webm', '.ogg', '.mov', '.jpg', '.jpeg', '.png', '.gif', '.webp']):
            content['links'].append({
                'url': href,
                'text': text
            })
    
    return content

def process_html_file(html_file, source_type):
    """Process a single HTML file and return structured content"""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get relative path for URL
        relative_path = os.path.relpath(html_file, f"scraped_{source_type}_content")
        
        # Extract content
        text_content = extract_text_content(soup)
        media_links = extract_media_links(soup, f"file://{relative_path}")
        
        return {
            'source': {
                'type': source_type,
                'file': relative_path,
                'timestamp': datetime.now().isoformat()
            },
            'content': {
                'text': text_content,
                'media': media_links
            }
        }
    except Exception as e:
        print(f"Error processing {html_file}: {str(e)}")
        return None

def process_directory(directory, source_type):
    """Process all HTML files in a directory"""
    all_content = {}
    html_files = glob.glob(os.path.join(directory, "**/*.html"), recursive=True)
    
    print(f"Processing {len(html_files)} files from {directory}...")
    
    for html_file in html_files:
        content = process_html_file(html_file, source_type)
        if content:
            # Create a nested structure based on the file path
            path_parts = os.path.dirname(content['source']['file']).split(os.sep)
            current_level = all_content
            
            # Create nested structure
            for part in path_parts:
                if part not in current_level:
                    current_level[part] = {}
                current_level = current_level[part]
            
            # Add the file content
            filename = os.path.basename(content['source']['file'])
            current_level[filename] = content
    
    return all_content

def main():
    # Create output directory if it doesn't exist
    output_dir = "json_content"
    os.makedirs(output_dir, exist_ok=True)
    
    # Process both directories
    platform_content = process_directory("scraped_content", "platform")
    support_content = process_directory("scraped_support_content", "support")
    
    # Combine all content
    combined_content = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_pages': len(glob.glob(os.path.join("scraped_content", "**/*.html"), recursive=True)) + 
                          len(glob.glob(os.path.join("scraped_support_content", "**/*.html"), recursive=True))
        },
        'content': {
            'platform': platform_content,
            'support': support_content
        }
    }
    
    # Save to JSON file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"combined_content_{timestamp}.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(combined_content, f, indent=2, ensure_ascii=False)
    
    print(f"\nProcessing complete!")
    print(f"Combined content saved to: {output_file}")

if __name__ == "__main__":
    main() 