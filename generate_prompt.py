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

logging.basicConfig(level=logging.INFO)

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


if __name__ == "__main__":
    file = "data/Valentino_Rossi/Valentino_Rossi.md"                      
    prompt_generator = WikipediaMovieGenerator()
    prompt = prompt_generator.process_file(file)
    prompt_path = prompt_generator.save_prompt(prompt, file)