# Wikipedia to Video

This project generates short videos from Wikipedia articles using AI.

## Description

This tool takes a Wikipedia URL as input, fetches the article's summary, and uses it to generate a script. The script is then used to create a short video using a text-to-video generation model. The process is divided into generating individual "episodes" which are then combined into a final video.


## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/USERNAME/wikipedia2video-testbed.git
   cd wikipedia2video-testbed
   ```

2. Create a virtual environment and activate it:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your environment variables. Create a `.env` file in the root of the project and add your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   REPLICATE_API_TOKEN=your_replicate_api_token
   ```

## Usage

You can run the script from the command line.

```bash
python main.py --urls <WIKIPEDIA_URL_1> <WIKIPEDIA_URL_2> --master-prompt <MASTER_PROMPT_FILE> --prompt-model <PROMPT_MODEL> --movie-model <MOVIE_MODEL> --episodes <NUMBER_OF_EPISODES>
```

### Arguments

- `--urls`: (Required) A list of one or more Wikipedia URLs to process.
- `--master-prompt`: (Optional) The path to a file containing the master prompt for the script generation. Defaults to `master_prompt_realistic_high_context_10_episodes.txt`. This file should be in the `inputs/` directory.
- `--prompt-model`: (Optional) The model to use for prompt generation (e.g., `gpt-4o`, `gpt-4o-mini`). Defaults to `gpt-4o`.
- `--movie-model`: (Optional) The model to use for video generation on Replicate (e.g., `pixverse/pixverse-v4.5`). Defaults to `pixverse/pixverse-v4.5`.
- `--episodes`: (Optional) The number of episodes to generate. Defaults to `10`.

### Example

```bash
python main.py --urls "https://en.wikipedia.org/wiki/Black_hole" --master-prompt "master_prompt_realistic_high_context_10_episodes.txt" --episodes 5
```

The generated videos will be saved in the `output/` directory, organized by article title.

## How it works

1.  **Fetch Summary**: For each Wikipedia URL, it fetches the page summary using the Wikipedia REST API.
2.  **Generate Prompt**: It uses a "master prompt" (a template configurable via inputs dir) and the Wikipedia summary to generate a detailed script for the video using an OpenAI model. The script is broken down into episodes. Via `prompt-model` arg the user can config which OpenAI model to use to generate the movie prompt. 
3.  **Generate Video Episodes**: For each episode in the script, it calls the Replicate API to generate a video clip using the specified text-to-video model. Via `movie-model` arg the user can config which Replicate model to use to generate the movie prompt. 
4.  **Combine Videos**: After all episode clips are generated, it uses `moviepy` to concatenate them into a single final video.

## Contributing

Contributions are welcome! Please feel free to submit a pull request.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details. 