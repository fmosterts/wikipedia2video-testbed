import requests
import json
import base64
import time
import os
import logging
import re
import replicate
import threading

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

class VideoGenerator:
    def __init__(self, page_name, output_dir, list_of_models):
        self.replicate_api_token = os.getenv("REPLICATE_API_TOKEN")
        self.list_of_models = list_of_models # example: ["google/veo-3"]
        self.output_dir = output_dir
        self.page_name = page_name

        with open(f"{self.output_dir}/{page_name}.movie_prompt.txt", "r") as f:
            self.prompt = f.read()

        with open(f"{self.output_dir}/{page_name}.png", "rb") as image_file:
            self.input_image_base64 = base64.b64encode(image_file.read()).decode('utf-8')

        # create video output directory
        self.video_output_dir = os.path.join(self.output_dir, f"videos")
        os.makedirs(self.video_output_dir, exist_ok=True)

        logging.info(f"Generating video samples given prompt: {self.prompt}")

        threads = []
        for model in self.list_of_models:
            thread = threading.Thread(target=self.generate_video_from_prompt_replicate, args=(model,))
            thread.start()
            threads.append(thread)
        
        for thread in threads:
            thread.join()

    def generate_video_from_prompt_replicate(self, model_id, duration=5):
        """Generate a video using Replicate and specified model, then save it."""

        logging.info(f"Generating video with Replicate using model {model_id}...")
        
        if model_id == "google/veo-2":
            input={
                "prompt": self.prompt,
                # "image": f"data:image/png;base64,{self.input_image_base64}",
                "aspect_ratio": "16:9",
                "duration": duration
            }
        elif model_id == "google/veo-3":
            input={
                "prompt": self.prompt,
                "aspect_ratio": "16:9",
            }
        
        elif model_id == "pixverse":
            input={
                "style": "None",
                # "image": f"data:image/png;base64,{self.input_image_base64}",
                "effect": "None",
                "prompt": self.prompt,
                "quality": "1080p",
                "duration": "8",
                "aspect_ratio": "16:9",
                "negative_prompt": ""
            }
            model_id = "pixverse/pixverse-v4.5"
        
        elif model_id == "minimax":
            input={
                "prompt": self.prompt,
                "first_frame_image": f"data:image/png;base64,{self.input_image_base64}",
            }
            model_id = "minimax/video-01-live"

        else:
            raise ValueError(f"Model {model_id} not supported")

        try:
            output = replicate.run(
                model_id,
                input
            )

            logging.info(f"Replicate returned output: {output}")

            safe_model_id = model_id.replace("/", "_")
            file_name = os.path.join(self.output_dir, f"/videos/{safe_model_id}.mp4")
            
            logging.info(f"Saving video to {file_name}")

            video_url = output
            if isinstance(output, list):
                video_url = output[0]
            
            response = requests.get(video_url)
            response.raise_for_status()

            with open(file_name, "wb") as file:
                file.write(response.content)


        except Exception as e:
            logging.error(f"Error during Replicate {model_id} video generation: {e}")
            return None 
    

def generatemovie_pixverse(pagename):
    video_generator = VideoGenerator(
        page_name=pagename,
        output_dir="data",
        list_of_models=["pixverse"]
    )
    
if __name__ == "__main__":
    video_generator = VideoGenerator(
        page_name="Valentino_Rossi",
        output_dir="data",
        list_of_models=["pixverse"]
    )