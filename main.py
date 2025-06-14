import logging
import os
import openai
import replicate
import asyncio
import aiohttp
import aiofiles

from dotenv import load_dotenv
from urllib.parse import urlparse

logging.basicConfig(level=logging.DEBUG)
load_dotenv()

async def download_video(url, save_dir, filename):
    filepath = os.path.join(save_dir, filename)

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            async with aiofiles.open(filepath, 'wb') as f:
                await f.write(await response.read())
    logging.info(f"Movie saved to {filepath}")

def clean_url(url_or_title):
    """Convert Wikipedia title or URL to a clean page title."""
    if url_or_title.startswith('http'):
        # Extract title from URL
        parsed = urlparse(url_or_title)
        title = parsed.path.split('/')[-1]
        return title
    else:
        return url_or_title

async def get_summary(session: aiohttp.ClientSession, wiki_url):
    '''
    Get the summary of a Wikipedia page
    '''
    title = clean_url(wiki_url)
    summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"

    logging.info(f"Fetching summary for {title}")
    try:
        async with session.get(summary_url) as response:
            response.raise_for_status()
            data = await response.json()
            logging.info(f"Summary for {title} fetched")
            return data
    except aiohttp.ClientError as e:
        logging.error(f"Error fetching summary: {e}")
        return None

async def generate_prompt(master_prompt, wiki_page_title, wiki_page_summary, save=True, output_filepath=None, model_id="gpt-4o-mini"):
    '''
    Generate a prompt for the movie given a master prompt, wiki page title, and wiki page summary
    '''
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    try:
        logging.info(f"Generating prompt for {wiki_page_title}")
        
        response = await client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": master_prompt},
                {"role": "user", "content": f"Title: {wiki_page_title}\nSummary: {wiki_page_summary}"}
            ]
        )
        
        prompt = response.choices[0].message.content
        logging.info(f"Prompt generated: {prompt}")

        if save and output_filepath:
            async with aiofiles.open(output_filepath, 'w', encoding='utf-8') as file:
                await file.write(prompt)
                logging.info(f"Prompt saved to {output_filepath}")

        return prompt
    
    except Exception as e:
        logging.error(f"Error generating prompt: {e}")
        raise

async def generate_movie_from_prompt(session: aiohttp.ClientSession, movie_prompt, output_filepath, title, model_id):
    '''
    Generate a movie from a prompt
    '''

    input_data={
        "prompt": movie_prompt
    }
    try:
        logging.info(f"Generating movie for: {title}")
        output = await asyncio.to_thread(replicate.run, model_id, input=input_data)

        logging.info(f"Replicate returned output: {output}")

        video_url = str(output)
        logging.debug(f"{video_url}")
        logging.info(f"Saving movie to {output_filepath}")
        # fix this getting error: Constructor parameter should be str
        # test url: https://replicate.delivery/xezq/lAbZYFfqZ5zUay7mMzug0BbtOMfoNwHO1u7CFtQmew3yCTtpA/tmpyu4lfpbm.mp4
        await download_video(video_url, output_filepath, f"{title}.mp4")

    except Exception as e:
        logging.error(f"{title}: Error during Replicate {model_id} video generation: {e}")
        return None 

async def generate_wiki_movie(session: aiohttp.ClientSession, wiki_url, master_prompt_path, prompt_model, movie_model):
    '''
    Get the movie prompt from the summary
    '''
    # Get the wiki page summary, title and output_dir
    wiki_page_metadata = await get_summary(session, wiki_url)
    title, wikipedia_page_summary = wiki_page_metadata["title"], wiki_page_metadata["extract"]
    sanitized_title = title.replace(' ', '_')
    output_dir = os.path.join(f"output", sanitized_title, master_prompt_path)
    os.makedirs(output_dir, exist_ok=True)

    # Get the movie prompt from the generator prompt + wiki page summary
    try:
        async with aiofiles.open(master_prompt_path, 'r', encoding='utf-8') as file:
            master_prompt = await file.read()
    except FileNotFoundError:
        logging.error(f"{master_prompt} not found. Please create it.")
        return None
    
    prompt_filepath = os.path.join(output_dir, f"{sanitized_title}.txt")
    prompt = await generate_prompt(master_prompt, title, wikipedia_page_summary, output_filepath=prompt_filepath, model=prompt_model)

    # Generate the movie
    await generate_movie_from_prompt(session, prompt, output_dir, title, movie_model)

    return prompt

async def main():
    wiki_url_list = ["https://en.wikipedia.org/wiki/The_Lord_of_the_Rings", 
                     "https://en.wikipedia.org/wiki/The_Hobbit"]
    master_prompt = "master_prompt_1.txt"
    prompt_model = "gpt-4o-mini"
    movie_model = "pixverse/pixverse-v4.5"
    
    async with aiohttp.ClientSession() as session:
        tasks = [generate_wiki_movie(session, 
                                     wiki_url, 
                                     master_prompt, 
                                     prompt_model,
                                     movie_model) for wiki_url in wiki_url_list]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())