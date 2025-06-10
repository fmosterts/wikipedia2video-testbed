# Wikipedia to Video Generator

This project automatically generates a short video from a Wikipedia article. It scrapes the content and main image from a given Wikipedia URL, uses a large language model (Claude) to generate a video prompt, and then uses a video generation API to create the video.

## Features

- Scrapes text and images from Wikipedia articles.
- Generates a creative video prompt using Anthropic's Claude API.
- Generates a video using a video generation API.
- Structured logging for better monitoring.
- Modular code for easy extension.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/wikipedia2video-testbed.git
    cd wikipedia2video-testbed
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Set up environment variables:**
    Create a `.env` file in the root of the project and add the following variables:

    ```
    # For video generation API
    PROJECT_ID="your-gcp-project-id"
    LOCATION_ID="us-central1"
    MODEL_ID="veo-2.0-generate-001"
    API_ENDPOINT="us-central1-aiplatform.googleapis.com"
    TOKEN_URL="http://your-token-service.com/token"

    # For prompt generation
    ANTHROPIC_API_KEY="your-anthropic-api-key"
    ```

## Usage

To generate a video, run the `main.py` script with the URL of the Wikipedia page as an argument:

```bash
python main.py "https://en.wikipedia.org/wiki/Steve_Jobs"
```

You can also specify the duration of the video in seconds (default is 10):

```bash
python main.py "https://en.wikipedia.org/wiki/Steve_Jobs" --duration 15
```

The generated files (markdown, prompt, and video) will be saved in the `data/<article-title>` directory.

## Customization

You can customize the generated video by editing the `generator_prompt.txt` file. This file contains the instructions that are provided to the language model (Claude) for generating the video prompt. By modifying this file, you can change the style, tone, and content of the videos.

For example, you can instruct the model to:
- Use a different directorial style (e.g., "like a Wes Anderson film").
- Change the pacing or structure of the video.
- Focus on specific aspects of the Wikipedia article.
- Add or remove specific types of shots (e.g., close-ups, wide shots).

Experiment with different prompts in `generator_prompt.txt` to see how it affects the final video output.
