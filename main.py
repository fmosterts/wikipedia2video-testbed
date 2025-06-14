from dotenv import load_dotenv
load_dotenv()

import argparse
import sys
import os
import logging

from wiki_scraper import WikipediaExtractor
from generate_prompt import WikipediaMovieGenerator
from video_generator import VideoGenerator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    parser = argparse.ArgumentParser(description="Wikipedia to Video Generator")
    parser.add_argument("wiki_url", help="The URL of the Wikipedia page to process.")
    parser.add_argument("--duration", type=int, default=8, required=False, help="Duration of the generated video in seconds.")
    parser.add_argument("--model_list", type=list, default=["minimax"], required=False, help="Model to use for video generation.") 
    parser.add_argument("--generate_prompt", type=bool, default=False, required=False, help="Generate prompt.")
    parser.add_argument("--generate_video", type=bool, default=False, required=False, help="Generate video.")
    parser.add_argument("--generate_image", type=bool, default=False, required=False, help="Generate image.")
    args = parser.parse_args()

    if args.generate_prompt == True:
        # Scrape Wikipedia
        extractor = WikipediaExtractor()
        output_dir, clean_title = extractor.create_outputdir(args.wiki_url)
        scraper_result = extractor.process_page(output_dir, clean_title)

        if not scraper_result['image_file']:
            logging.error("Could not download an image from the Wikipedia page. Exiting.")

        # Generate prompt
        prompt_generator = WikipediaMovieGenerator()
        prompt = prompt_generator.process_file(scraper_result['markdown_file'])
        prompt_path = prompt_generator.save_prompt(prompt, scraper_result['markdown_file'])

    if args.generate_video == True:
        # Generate video
        video_generator = VideoGenerator(
            page_name=clean_title,
            output_dir=output_dir,
            list_of_models=args.model_list
        )


if __name__ == "__main__":
    main()