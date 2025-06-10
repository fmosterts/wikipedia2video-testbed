import sys
import os
from pathlib import Path
from typing import Optional
import json
from anthropic import Anthropic
import logging
import argparse

from dotenv import load_dotenv
load_dotenv()


class WikipediaMovieGenerator:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with Claude API key."""
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("API key must be provided or set as ANTHROPIC_API_KEY environment variable")
        
        self.client = Anthropic(api_key=self.api_key)
    
    def create_analysis_prompt(self, markdown_content: str) -> str:
        """Create the prompt for Claude to analyze Wikipedia content."""
        
        with open("generator_prompt.txt", "r") as f:
            prompt = f.read() + markdown_content
        
        return prompt

    def generate_movie_prompt(self, markdown_content: str) -> str:
        """Send content to Claude and get movie prompt."""
        try:
            analysis_prompt = self.create_analysis_prompt(markdown_content)
            
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2500,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ]
            )
            
            return message.content[0].text
            
        except Exception as e:
            raise Exception(f"Error calling Claude API: {str(e)}")
    
    def process_file(self, markdown_file: Path) -> str:
        """Process a single markdown file and generate movie prompt."""
        
        # Read the markdown file
        try:
            with open(markdown_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            raise Exception(f"Error reading file: {str(e)}")
        
        if len(content.strip()) == 0:
            raise ValueError("File appears to be empty")
        
        # Generate movie prompt using Claude
        logging.info("Analyzing Wikipedia content for movie potential...")
        movie_prompt = self.generate_movie_prompt(content)
        
        return movie_prompt
    
    def save_prompt(self, prompt: str, original_file: Path) -> Path:
        """Save the generated prompt to a file."""
        output_file = original_file[:-3] + '.movie_prompt.txt'
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(prompt)
            logging.info("Movie prompt saved to: %s", output_file)
            return output_file
        except Exception as e:
            raise Exception(f"Error saving output file: {str(e)}")


def main():
    """Main function to run the movie prompt generator."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    parser = argparse.ArgumentParser(description="Generate a movie prompt from a Wikipedia markdown file.")
    parser.add_argument("markdown_file", type=Path, help="Path to the markdown file.")
    args = parser.parse_args()

    try:
        # Initialize the generator
        generator = WikipediaMovieGenerator()
        
        # Process the file
        logging.info("Processing: %s", args.markdown_file)
        movie_prompt = generator.process_file(args.markdown_file)
        
        # Display the result
        logging.info("\n" + "="*80)
        logging.info("GENERATED MOVIE PROMPT")
        logging.info("="*80)
        logging.info(movie_prompt)
        
        # Save to file
        generator.save_prompt(movie_prompt, args.markdown_file)
        
    except FileNotFoundError as e:
        logging.error("Error: %s", e)
        sys.exit(1)
    except ValueError as e:
        logging.error("Error: %s", e)
        sys.exit(1)
    except Exception as e:
        logging.error("Unexpected error: %s", e)
        sys.exit(1)
