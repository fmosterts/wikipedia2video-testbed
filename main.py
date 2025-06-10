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
    parser.add_argument("--duration", type=int, default=8, help="Duration of the generated video in seconds.")
    args = parser.parse_args()

    project_id = os.getenv('PROJECT_ID')
    location_id = os.getenv('LOCATION_ID')
    model_id = os.getenv('MODEL_ID')
    api_endpoint = os.getenv('API_ENDPOINT')
    token_url = os.getenv('TOKEN_URL')

    if not all([project_id, location_id, model_id, api_endpoint, token_url]):
        logging.error("Missing one or more required environment variables.")
        sys.exit(1)

    # Scrape Wikipedia
    extractor = WikipediaExtractor()
    output_dir, clean_title = extractor.create_outputdir(args.wiki_url)
    scraper_result = extractor.process_page(output_dir, clean_title)

    if not scraper_result['image_file']:
        logging.error("Could not download an image from the Wikipedia page. Exiting.")
        sys.exit(1)

    # Generate prompt
    prompt_generator = WikipediaMovieGenerator()
    prompt = prompt_generator.process_file(scraper_result['markdown_file'])
    prompt_path = prompt_generator.save_prompt(prompt, scraper_result['markdown_file'])

    # Generate video
    video_gen = VideoGenerator(project_id, location_id, model_id, api_endpoint, token_url)
    operation_id = video_gen.start_video_generation(prompt_path, scraper_result['image_file'], args.duration)

    if not operation_id:
        logging.error("Failed to start video generation.")
        sys.exit(1)

    # Poll for completion
    result = video_gen.poll_for_completion(operation_id)
    if not result:
        logging.error("Video generation polling failed.")
        sys.exit(1)

    # Save videos
    if video_gen.save_videos(result, metafile_name=clean_title, output_dir=output_dir):
        logging.info("Video generation completed successfully!")
    else:
        logging.error("Error saving videos.")
        sys.exit(1)

if __name__ == "__main__":
    main()