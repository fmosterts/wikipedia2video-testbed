import requests
import re
import os
import sys
from urllib.parse import urlparse, urljoin, unquote
from bs4 import BeautifulSoup
from PIL import Image
import html2text
import argparse
import logging

logging.basicConfig(level=logging.INFO)

class WikipediaExtractor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Wikipedia-Extractor/1.0 (Educational purposes)'
        })
    
    def clean_url(self, url_or_title):
        """Convert Wikipedia title or URL to a clean page title."""
        if url_or_title.startswith('http'):
            # Extract title from URL
            parsed = urlparse(url_or_title)
            title = parsed.path.split('/')[-1]
            return title
        return url_or_title
    
    def get_wikipedia_url(self, title):
        """Convert page title to Wikipedia URL."""
        clean_title = title.replace(' ', '_')
        return f"https://en.wikipedia.org/wiki/{clean_title}"
    
    def fetch_page(self, title):
        """Fetch Wikipedia page content."""
        url = self.get_wikipedia_url(title)
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            raise Exception(f"Failed to fetch Wikipedia page: {e}")
    
    def extract_main_image(self, soup):
        """Extract the main image URL from the Wikipedia page."""
        # Try to find the main infobox image first
        infobox = soup.find('table', class_='infobox')
        if infobox:
            img_tag = infobox.find('img')
            if img_tag and img_tag.get('src'):
                src = img_tag.get('src')
                # Check for thumbnail URL and try to get full-size version
                if '/thumb/' in src:
                    # e.g. //.../thumb/a/a9/Example.jpg/220px-Example.jpg
                    # becomes //.../a/a9/Example.jpg
                    src = re.sub(r'(/thumb)(/.*)/[^/]*$', r'\2', src)
                return src

        # Look for the first image in the content area that meets size requirements
        content = soup.find('div', {'id': 'mw-content-text'})
        if content:
            images = content.find_all('img')
            for img in images:
                src = img.get('src', '')
                
                # Basic filter for unwanted images
                if any(skip in src.lower() for skip in ['commons-logo', 'wikimedia', 'edit-icon']):
                    continue
                    
                width_attr = img.get('width')
                height_attr = img.get('height')

                if width_attr and height_attr:
                    try:
                        width = int(width_attr)
                        height = int(height_attr)
                        if min(width, height) >= 300:
                            return src
                    except ValueError:
                        # Ignore if width/height are not integer values
                        pass
        
        return None
    
    def download_image(self, img_url, filename):
        """Download and convert image to PNG."""
        if not img_url:
            logging.warning("No main image found")
            return False
        
        # Handle protocol-relative URLs
        if img_url.startswith('//'):
            img_url = 'https:' + img_url
        elif img_url.startswith('/'):
            img_url = 'https://en.wikipedia.org' + img_url
        
        try:
            logging.info("Downloading image from: %s", img_url)
            response = self.session.get(img_url)
            response.raise_for_status()
            
            # Save as PNG
            with open('temp_image', 'wb') as f:
                f.write(response.content)
            
            # Convert to PNG using PIL
            with Image.open('temp_image') as img:
                # Check image dimensions
                width, height = img.size
                if min(width, height) < 300:
                    logging.warning(f"Image is too small ({width}x{height}), skipping.")
                    os.remove('temp_image')
                    return False
                
                # Convert to RGB if necessary (for images with transparency)
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                img.save(filename, 'PNG')
            
            # Clean up temp file
            os.remove('temp_image')
            logging.info("Image saved as: %s", filename)
            return True
            
        except Exception as e:
            logging.error("Failed to download image: %s", e)
            if os.path.exists('temp_image'):
                os.remove('temp_image')
            return False
    
    def convert_to_markdown(self, soup):
        """Convert Wikipedia content to markdown."""
        # Remove unwanted elements
        for element in soup.find_all(['script', 'style', 'sup', 'div'], class_=['navbox', 'reflist', 'reference']):
            element.decompose()
        
        # Remove edit links
        for element in soup.find_all('span', class_='mw-editsection'):
            element.decompose()
        
        # Get the main content
        content = soup.find('div', {'id': 'mw-content-text'})
        if not content:
            raise Exception("Could not find main content area")
        
        # Configure html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True  # We handle the main image separately
        h.ignore_emphasis = False
        h.body_width = 0  # Don't wrap lines
        h.unicode_snob = True
        h.skip_internal_links = True
        
        # Convert to markdown
        markdown_content = h.handle(str(content))
        
        # Clean up the markdown
        # Remove multiple consecutive empty lines
        markdown_content = re.sub(r'\n\s*\n\s*\n', '\n\n', markdown_content)
        
        # Remove Wikipedia-specific formatting
        markdown_content = re.sub(r'\[\s*edit\s*\]', '', markdown_content, flags=re.IGNORECASE)
        
        return markdown_content.strip()
    
    def extract_page_info(self, soup):
        """Extract basic page information."""
        title = soup.find('h1', {'id': 'firstHeading'})
        title_text = title.get_text() if title else "Unknown"
        
        return {
            'title': title_text,
            'url': soup.find('link', {'rel': 'canonical'})['href'] if soup.find('link', {'rel': 'canonical'}) else ''
        }
    
    def create_outputdir(self, title_or_url):
        # Clean the input
        clean_title = self.clean_url(title_or_url)
        
        logging.info("Processing Wikipedia page: %s", clean_title)
        
        output_dir = f"data/{clean_title}"
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        return output_dir, clean_title
    
    def process_page(self, output_dir, clean_title):
        """Main method to process a Wikipedia page."""
        # Fetch the page
        html_content = self.fetch_page(clean_title)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract page info
        page_info = self.extract_page_info(soup)
        
        # Create safe filename
        safe_filename = re.sub(r'[^\w\s-]', '', page_info['title'])
        safe_filename = re.sub(r'[-\s]+', '_', safe_filename).strip('_')
        
        # Convert to markdown
        logging.info("Converting to markdown...")
        markdown_content = self.convert_to_markdown(soup)
        
        # Add header with page info
        header = f"# {page_info['title']}\n\n"
        if page_info['url']:
            header += f"**Source:** {page_info['url']}\n\n"
        header += "---\n\n"
        
        markdown_content = header + markdown_content
        
        # Save markdown
        md_filename = os.path.join(output_dir, f"{safe_filename}.md")
        with open(md_filename, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        logging.info("Markdown saved as: %s", md_filename)
        
        # Download main image
        logging.info("Looking for main image...")
        img_url = self.extract_main_image(soup)
        img_filename = os.path.join(output_dir, f"{safe_filename}.png")
        image_downloaded = self.download_image(img_url, img_filename)
        
        return {
            'markdown_file': md_filename,
            'image_file': img_filename if image_downloaded else None,
            'title': page_info['title']
        }

if __name__ == "__main__":
    wiki_url = "https://en.wikipedia.org/wiki/Valentino_Rossi"
    extractor = WikipediaExtractor()
    output_dir, clean_title = extractor.create_outputdir(wiki_url)
    scraper_result = extractor.process_page(output_dir, clean_title)