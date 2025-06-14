import logging
import requests
import os
import openai
import replicate

from dotenv import load_dotenv
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO)
load_dotenv()

def clean_url(url_or_title):
    """Convert Wikipedia title or URL to a clean page title."""
    if url_or_title.startswith('http'):
        # Extract title from URL
        parsed = urlparse(url_or_title)
        title = parsed.path.split('/')[-1]
        return title
    else:
        logging.error(f"Invalid URL: {url_or_title}")

def get_summary(wiki_url):
    '''
    Get the summary of a Wikipedia page
    '''
    title = clean_url(wiki_url)
    summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"

    logging.info(f"Fetching summary for {title}")
    try:
        response = requests.get(summary_url)
        response.raise_for_status()
        logging.info(f"Summary fetched: {response.json()}")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching summary: {e}")
        return None

def generate_prompt(master_prompt, wiki_page_title, wiki_page_summary, save=True, output_filepath=None):
    '''
    Generate a prompt for the movie given a master prompt, wiki page title, and wiki page summary
    '''
    openai.api_key = os.getenv("OPENAI_API_KEY")
    logging.info(f"Generating prompt for {wiki_page_title}")
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": master_prompt},
            {"role": "user", "content": f"Title: {wiki_page_title}\nSummary: {wiki_page_summary}"}
        ]
    )
    logging.info(f"Prompt generated: {response.choices[0].message.content}")
    prompt = response.choices[0].message.content

    if save and output_filepath:
        with open(output_filepath, 'w', encoding='utf-8') as file:
            file.write(prompt)
            logging.info(f"Prompt saved to {output_filepath}")
    return prompt

def generate_movie_from_prompt(movie_prompt, output_filepath):
    '''
    Generate a movie from a prompt
    '''
    model_id = "pixverse/pixverse-v4.5"
    input={
        "prompt": movie_prompt    }
    try:
        logging.info(f"Generating movie with prompt: {movie_prompt}")
        output = replicate.run(
            model_id,
            input
        )

        logging.info(f"Replicate returned output: {output}")

        video_url = output
        if isinstance(output, list):
            video_url = output[0]
        
        response = requests.get(video_url)
        response.raise_for_status()

        with open(output_filepath, "wb") as file:
            file.write(response.content)
        logging.info(f"Movie saved to {output_filepath}")

    except Exception as e:
        logging.error(f"Error during Replicate {model_id} video generation: {e}")
        return None 

def generate_wiki_movie(wiki_url):
    '''
    Get the movie prompt from the summary
    '''
    # Get the wiki page summary and title
    wiki_page_metadata = get_summary(wiki_url)
    title, wikipedia_page_summary = wiki_page_metadata["title"], wiki_page_metadata["extract"]
    
    sanitized_title = title.replace(' ', '_')
    output_dir = os.path.join("output", sanitized_title)
    os.makedirs(output_dir, exist_ok=True)

    # Get the movie prompt from the generator prompt + wiki page summary
    with open("generator_prompt.txt", 'r', encoding='utf-8') as file:
        master_prompt = file.read()
    
    prompt_filepath = os.path.join(output_dir, f"{sanitized_title}.txt")
    prompt = generate_prompt(master_prompt, title, wikipedia_page_summary, output_filepath=prompt_filepath)

    # Generate the movie
    movie_filepath = os.path.join(output_dir, f"{sanitized_title}.mp4")
    generate_movie_from_prompt(prompt, movie_filepath)

    return prompt

if __name__ == "__main__":
    wiki_url = "https://en.wikipedia.org/wiki/The_Lord_of_the_Rings"
    generate_wiki_movie(wiki_url)