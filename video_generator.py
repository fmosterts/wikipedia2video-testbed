import requests
import json
import base64
import time
import os
import logging
import re

class VideoGenerator:
    def __init__(self, project_id, location_id, model_id, api_endpoint, token_url):
        self.project_id = project_id
        self.location_id = location_id
        self.model_id = model_id
        self.api_endpoint = api_endpoint
        self.token_url = token_url
        self.token = None

    def fetch_token(self):
        """Fetch authentication token from the token service."""
        logging.info("Fetching authentication token...")
        try:
            response = requests.get(self.token_url)
            response.raise_for_status()
            token_data = response.json()

            if 'access_token' not in token_data:
                logging.error("Could not extract access_token from response. Response: %s", token_data)
                return None

            logging.info("Token fetched successfully")
            self.token = token_data['access_token']
            return self.token

        except requests.RequestException as e:
            logging.error("Could not fetch token from %s. Error: %s", self.token_url, e)
            return None
        except json.JSONDecodeError as e:
            logging.error("Invalid JSON response from token service. Error: %s", e)
            return None

    def start_video_generation(self, prompt_path, image_path, durationSeconds, output_count):
        """Start the video generation process."""
        if not self.token:
            self.fetch_token()
            if not self.token:
                return None

        url = f"https://{self.api_endpoint}/v1/projects/{self.project_id}/locations/{self.location_id}/publishers/google/models/{self.model_id}:predictLongRunning"

        try:
            with open(prompt_path, "r") as f:
                content = f.read()
        except FileNotFoundError:
            logging.error(f"Prompt file not found: {prompt_path}")
            return None

        match = re.search(r'<prompts>(.*?)</prompts>', content, re.DOTALL)
        if not match:
            logging.error(f"Could not find <prompts>...</prompts> in {prompt_path}")
            return None
        
        prompt = match.group(1).strip()
            
        payload = {
            "endpoint": f"projects/{self.project_id}/locations/{self.location_id}/publishers/google/models/{self.model_id}",
            "instances": [
                {
                    "prompt": prompt,
                    "image": {
                        "bytesBase64Encoded": base64.b64encode(open(image_path, "rb").read()).decode("utf-8"),
                        "mimeType": "image/png"
                    }
                }
            ],
            "parameters": {
                "aspectRatio": "16:9",
                "sampleCount": output_count,
                "durationSeconds": durationSeconds,
                "personGeneration": "allow_adult",
                "enablePromptRewriting": True,
                "addWatermark": True,
                "includeRaiReason": True
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

        logging.info("Generating video with prompt: %s", prompt)
        logging.info("Starting video generation...")

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

            if 'name' not in result:
                logging.error("Could not extract operation ID from response. Response: %s", result)
                return None

            operation_id = result['name']
            logging.info("Operation ID: %s", operation_id)
            return operation_id

        except requests.RequestException as e:
            logging.error("Error starting video generation: %s", e)
            return None

    def poll_for_completion(self, operation_id):
        """Poll for video generation completion."""
        if not self.token:
            logging.error("No token available for polling.")
            return None

        url = f"https://{self.api_endpoint}/v1/projects/{self.project_id}/locations/{self.location_id}/publishers/google/models/{self.model_id}:fetchPredictOperation"

        payload = {"operationName": operation_id}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

        poll_interval = 10
        logging.info("Waiting for video generation to complete...")

        while True:
            logging.info("Checking status...")

            try:
                response = requests.post(url, json=payload, headers=headers)
                response.raise_for_status()
                result = response.json()

                if result.get('done', False):
                    logging.info("Operation completed!")

                    if 'error' in result:
                        logging.error("Error in operation: %s", result['error'])
                        return None

                    return result

                else:
                    logging.info("Operation still in progress... waiting %s seconds", poll_interval)
                    time.sleep(poll_interval)

            except requests.RequestException as e:
                logging.error("Error polling for completion: %s", e)
                return None

    def save_videos(self, response_data, metafile_name, output_dir):
        """Extract and save video files from the response."""
        folder = f"{output_dir}/videos"
        if not os.path.exists(folder):
            os.makedirs(folder)

        # Save full response for debugging
        with open(f'{folder}/{metafile_name}.json', 'w') as f:
            json.dump(response_data, f, indent=2)

        videos = response_data.get('response', {}).get('videos', [])

        if not videos:
            logging.warning("No videos found in response")
            return False

        video_count = len(videos)
        logging.info("Found %d video(s). Extracting...", video_count)

        for i, video in enumerate(videos):
            output_file = f"{folder}/{metafile_name}_{i}.mp4"

            try:
                video_data = base64.b64decode(video['bytesBase64Encoded'])
                with open(output_file, 'wb') as f:
                    f.write(video_data)
                logging.info("Saved video %d to: %s", i, output_file)

            except Exception as e:
                logging.error("Error saving video %d: %s", i, e)
                return False

        return True 