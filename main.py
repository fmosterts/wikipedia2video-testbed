import logging
import os
import openai
import replicate
import asyncio
import aiohttp
import aiofiles
import re
import argparse

from elevenlabs import ElevenLabs
from moviepy import VideoFileClip, concatenate_videoclips

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

async def combine_episodes(output_dir, n_episodes, sanitized_title):
    '''Combine the episodes into a single video'''
    clips = []

    for episode in range(0, n_episodes):  # include episode n_episodes
        try:
            episode_filepath = os.path.join(output_dir, f"{sanitized_title}_episode_{episode}.mp4")
            if not os.path.exists(episode_filepath):
                logging.error(f"Episode {episode} not found at {episode_filepath}")
                continue
            clip = VideoFileClip(episode_filepath)
            clips.append(clip)
        except Exception as e:
            logging.error(f"Error loading episode {episode}: {e}")
            continue

    if not clips:
        logging.error("No clips found to combine.")
        return None

    final_clip = concatenate_videoclips(clips, method="compose")
    output_filepath = os.path.join(output_dir, f"{sanitized_title}.mp4")
    final_clip.write_videofile(output_filepath)
    logging.info(f"Combined episodes saved to {output_filepath}")

async def get_separated_portion_prompt(prompt, n_episodes):
    '''Given a prompt that separates episodes by "Episode {episode_number}:", return a list of prompts for each episode'''

    # Use regex to split the episodes
    episodes = re.split(r'(Episode \d+:)', prompt)
    # Combine episode headers with their corresponding text
    episode_strings = [episodes[i] + episodes[i+1] for i in range(1, len(episodes), 2)]
    if len(episode_strings) != n_episodes:
        logging.error(f"Number of episodes in prompt does not match n_episodes: {len(episode_strings)} != {n_episodes}")
        return None
    
    return episode_strings

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
        await download_video(video_url, output_filepath, f"{title}")

    except Exception as e:
        logging.error(f"{title}: Error during Replicate {model_id} video generation: {e}")
        return None 

async def generate_wiki_movie(session: aiohttp.ClientSession, wiki_url, master_prompt_path, prompt_model, movie_model, n_episodes=1):
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
        async with aiofiles.open(f"inputs/{master_prompt_path}", 'r', encoding='utf-8') as file:
            master_prompt = await file.read()
    except FileNotFoundError:
        logging.error(f"{master_prompt} not found. Please create it.")
        return None
    
    prompt_filepath = os.path.join(output_dir, f"{sanitized_title}.txt")
    prompt = await generate_prompt(master_prompt, title, wikipedia_page_summary, output_filepath=prompt_filepath, model_id=prompt_model)

    # Generate the episodes
    separated_prompts_per_episode = await get_separated_portion_prompt(prompt, n_episodes)
    n_episode = 0
    tasks = []
    for episode_prompt in separated_prompts_per_episode:
        title = f"{sanitized_title}_episode_{n_episode}.mp4"
        tasks.append(generate_movie_from_prompt(session, episode_prompt, output_dir, title, movie_model))
        n_episode += 1
    await asyncio.gather(*tasks)

    # Combine the episodes
    try:
        await combine_episodes(output_dir, n_episodes, sanitized_title)
    except Exception as e:
        logging.error(f"Error combining episodes: {e}")
        return None

    return None


async def generate_audio_from_summary(summary, output_filepath):
    """
    Generate speech audio from text using ElevenLabs API
    """
    # TODO: Fix this!
    try:
        client = ElevenLabs(
        api_key="YOUR_API_KEY",
        )
        audio = await client.text_to_speech.convert(
            voice_id="JBFqnCBsd6RMkjVDRZzb",
            output_format="mp3_44100_128",
            text=summary,
            model_id="eleven_multilingual_v2",
        )
        print(audio)
        # Save the audio to a file
        with open(output_filepath, "wb") as f:
            f.write(audio)
        return audio
    except Exception as e:
        logging.error(f"Error generating audio: {e}")

 

async def main():

    parser = argparse.ArgumentParser(description='Generate mini-series from Wikipedia articles')
    parser.add_argument('--urls', nargs='+', required=True,
                      help='List of Wikipedia URLs to process')
    parser.add_argument('--master-prompt', default="master_prompt_realistic_high_context_10_episodes.txt",
                      help='Master prompt template file (default: master_prompt_realistic_high_context_10_episodes.txt)')
    parser.add_argument('--prompt-model', default="gpt-4o",
                      help='Model to use for prompt generation (default: gpt-4o)')
    parser.add_argument('--movie-model', default="pixverse/pixverse-v4.5",
                      help='Model to use for video generation (default: pixverse/pixverse-v4.5)')
    
    # TODO fix dependency on number of episodes hardcoded in prompt
    parser.add_argument('--episodes', type=int, default=10,
                      help='Number of episodes to generate (default: 10)')
    
    args = parser.parse_args()
    
    async with aiohttp.ClientSession() as session:
        tasks = [generate_wiki_movie(session,
                                   wiki_url,
                                   args.master_prompt,
                                   args.prompt_model, 
                                   args.movie_model,
                                   args.episodes) for wiki_url in args.urls]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())