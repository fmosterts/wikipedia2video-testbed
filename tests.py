# Test to connect all videos in a folder
import asyncio
from main import *

async def test_combine_episodes():
    sanitized_title = "Ethereum"
    output_dir = f"output/{sanitized_title}/master_prompt_realistic_high_context_10_episodes.txt"
    n_episodes = 10
    await combine_episodes(output_dir, n_episodes, sanitized_title)



async def main():
    summary = "Ethereum is a decentralized blockchain with smart contract functionality. Ether is the native cryptocurrency of the platform. Among cryptocurrencies, ether is second only to bitcoin in market capitalization. It is open-source software."

    summary = await generate_audio_from_summary(summary, output_filepath="output/Ethereum/audio.mp3")


if __name__ == "__main__":
    asyncio.run(main())





