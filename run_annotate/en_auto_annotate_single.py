# auto_annotate_merged.py (只传入current图片，支持多模型，通过命令行指定，新增Gemini Pro，全英文Prompt，标注文件存入annotations目录)

import os
import json
import time
import glob
import base64
import argparse
from collections import defaultdict
from openai import OpenAI

# --- Configuration (OpenAI / OpenRouter) ---
# Please replace YOUR_OPENROUTER_API_KEY_HERE with your actual OpenRouter API key
OPENAI_API_KEY = "YOUR_OPENROUTER_API_KEY_HERE"

# OpenRouter.ai specific configuration
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# --- Constants ---
IMAGE_DATA_ROOT = "overlap_visualizations_3_sampled_complete"
ANNOTATIONS_DIR = "annotations_2" # 标注文件存放目录

    # --- Model Configuration Mapping ---
MODEL_CONFIGS = {
    "openai": {
        "model_name": "openai/gpt-4o-mini",
        "annotations_file": "annotations_openai.json"
    },
    "qwen": {
        "model_name": "qwen/qwen2.5-vl-72b-instruct",
        "annotations_file": "annotations_qwen.json"
    },
    "llama": {
        "model_name": "meta-llama/llama-4-maverick",
        "annotations_file": "annotations_llama.json"
    },
    "gemini_20_flash": {
        "model_name": "google/gemini-2.0-flash-001",
        "annotations_file": "annotations_gemini_20_flash.json"
    },
    "gemini_continue": {
        "model_name": "google/gemini-2.0-flash-001",
        "annotations_file": "annotations_gemini_1.json"
    },
    "gemini_25_flash": {
        "model_name": "google/gemini-2.5-flash-preview-05-20",
        "annotations_file": "annotations_gemini_25_flash.json"
    },
    "gemini_pro": {
        "model_name": "google/gemini-2.5-pro",
        "annotations_file": "annotations_gemini_pro.json"
    },
    "gemini_free": {
        "model_name": "google/gemini-2.0-flash-exp:free",
        "annotations_file": "annotations_free.json"
    },
    "qwen_free": {
        "model_name": "qwen/qwen2.5-vl-32b-instruct:free",
        "annotations_file": "annotations_qwen_free.json"
    },
    "mistral_free": {
        "model_name": "mistralai/mistral-small-3.1-24b-instruct:free",
        "annotations_file": "annotations_mistral_free.json"
    },
    "gemma_free": {
        "model_name": "google/gemma-3-27b-it:free",
        "annotations_file": "annotations_gemma_free.json"
    }
}

# --- ###################### Core Modification: New PROMPT Definition, refined and translated ###################### ---
PROMPT_INSTRUCTIONS = """
You are a top-tier mobile application performance optimization expert and a senior Android/iOS engineer.

### Your Core Task:
Analyze the given UI screenshot to determine if a performance issue, specifically "a high-cost component being significantly obscured," has occurred in the `current` image, and to provide specific code-level optimization suggestions.

### Definition of "High-Cost Component" (Key Judgment Criteria):
1.  **Heavy Rendering Type**: Video Player, Complex Animation, Map, Camera Preview, Long Image List, WebView.
2.  **Heavy Computation/IO Type**: Must be **real-time refreshing components**, such as Complex Chart, Data-Heavy List that update frequently. Components merely containing extensive text and icons without real-time refreshing are NOT considered high-cost.

### Definition of "Significantly Obscured":
Refers to another UI element (e.g., a pop-up, ActionSheet, advertisement, or another card) covering most or all of the "high-cost component," making its content invisible or non-interactive to the user.

### Your Analysis Process:
1.  **Identify**: First, carefully examine the `current` image to determine if any "high-cost components" exist.
2.  **Determine**:
    *   If **no** "high-cost components" are found, the conclusion is **"No"**.
    *   If one or more "high-cost components" **exist**, then determine if it is **significantly obscured**.
    *   If obscured, the conclusion is **"Yes"**.
    *   If not obscured, or if the obscuring element is very small, the conclusion is **"No"**.
3.  **Ignore Screenshot Imperfections**: If content is abruptly cut off at the image edges, this is a screenshot tool issue, **not an obscuring problem**, and should be ignored.

### Output Requirements:
Your response **must** be a single, valid JSON object, without any other explanatory text or Markdown formatting. The JSON object must contain only three keys:
1.  `"label"`: String, value must be `"Yes"` or `"No"`.
2.  `"reason"`: A concise English explanation stating your judgment basis.
    *   If `Yes`, the reason must clearly explain **"what high-cost component is obscured by what"** (e.g., "The video player is obscured by a login pop-up").
    *   If `No`, the reason must state **"No high-cost component detected"** or **"High-cost component (e.g., map) exists but is not obscured"**.
3.  `"solution"`: String, providing specific, actionable optimization suggestions.
    *   If `label` is `Yes`, provide code-level optimization suggestions (e.g., "When the pop-up appears, pause video rendering by calling `videoView.pause()`, and resume it by calling `videoView.resume()` after the pop-up closes. Or, in RecyclerView, release obscured video resources via the `onViewDetachedFromWindow` callback.").
    *   If `label` is `No`, the `solution` value should be "No optimization needed".
"""
# --- ############################## PROMPT Modification End ############################## ---

def deep_defaultdict(): return defaultdict(deep_defaultdict)

def load_annotations(annotations_file):
    if not os.path.exists(annotations_file): return deep_defaultdict()
    try:
        with open(annotations_file, 'r', encoding='utf-8') as f: data = json.load(f)
        annotations = deep_defaultdict()
        for app, samples in data.items():
            for sample_id, annos in samples.items():
                if isinstance(annos, dict):
                    if 'ai' in annos or 'human' in annos: annotations[app][sample_id].update(annos)
                    else: annotations[app][sample_id]['human'] = annos
                elif isinstance(annos, str):
                    annotations[app][sample_id]['human'] = {"label": annos, "annotator": "Human"}
        return annotations
    except (FileNotFoundError, json.JSONDecodeError): return deep_defaultdict()

def save_annotations(data, annotations_file):
    # Ensure target directory exists
    os.makedirs(os.path.dirname(annotations_file), exist_ok=True)
    def convert_to_dict(item):
        if isinstance(item, defaultdict): return {k: convert_to_dict(v) for k, v in item.items()}
        return item
    regular_dict = convert_to_dict(data)
    with open(annotations_file, 'w', encoding='utf-8') as f: json.dump(regular_dict, f, indent=4, ensure_ascii=False)

def find_image_paths(app_name, sample_id):
    """
    Finds the path for the 'current' image.
    'before' and 'after' images are no longer needed for this modified script.
    """
    paths = {}
    # Only look for the 'current' image
    pattern = os.path.join(IMAGE_DATA_ROOT, app_name, f"{sample_id}__current*.png")
    found_files = glob.glob(pattern)
    if found_files:
        paths['current'] = found_files[0]

    import re
    if paths['current']:
        current_path = paths['current']
        current_filename = os.path.basename(current_path)
        # 匹配 screenCap_数字.png
        match = re.search(r"(screenCap_\d+)\.png", current_filename)
        if match:
            screen_cap_name = match.group(1) + ".png"
            # 构造原始current图片路径
            orig_current_path = os.path.join(r"D:\Code\HapTest\day10_simple", app_name, screen_cap_name)
            if os.path.exists(orig_current_path):
                paths['current'] = orig_current_path

    # for state in ['before', 'current', 'after']:
    #     print(f"  {state}: {paths.get(state)}")

    return paths

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def annotate_sample_with_ai(client, app_name, sample_id, model_name):
    print(f"Processing: {app_name} / {sample_id} (Model: {model_name})")
    image_paths = find_image_paths(app_name, sample_id)

    # Only check for the existence of the 'current' image
    if not image_paths['current']:
        print(f"  -> Skipping: Could not find the 'current' image.")
        return None

    messages_content = []
    messages_content.append({"type": "text", "text": PROMPT_INSTRUCTIONS})

    try:
        # Only process the 'current' image
        current_image_path = image_paths['current']
        base64_image = encode_image(current_image_path)
        messages_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{base64_image}"
            }
        })
    except IOError as e:
        print(f"  -> Skipping: Error reading image file. Error: {e}")
        return None

    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": messages_content
                }
            ],
            extra_headers={
                "HTTP-Referer": "https://your-app-domain.com",
                "X-Title": "Mobile App Performance Annotation Tool",
            },
            timeout=240.0
        )
        raw_text = completion.choices[0].message.content

        first_brace, last_brace = raw_text.find('{'), raw_text.rfind('}')
        if first_brace == -1 or last_brace == -1:
            print(f"  -> JSON parsing error: No valid JSON structure found in model response. Response: {raw_text}"); return None
        json_str = raw_text[first_brace : last_brace + 1]
        result = json.loads(json_str)

        if 'label' in result and 'reason' in result and 'solution' in result and result['label'] in ['Yes', 'No']:
            print(f"  -> Success: AI classified as {result['label']}.")
            result['annotator'] = 'AI'
            result['model_used'] = model_name
            result['annotation_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
            return result
        else:
            print(f"  -> Parsing error: AI response JSON is invalid or missing keys. Response: {raw_text}"); return None
            
    except json.JSONDecodeError as e:
        print(f"  -> JSON parsing error: Could not parse extracted string. Error: {e}. Extracted content: '{json_str}'"); return None
    except Exception as e:
        print(f"  -> API or other unknown error: {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Annotate mobile app UI screenshots for performance using OpenRouter API.")
    parser.add_argument(
        "--model",
        type=str,
        choices=MODEL_CONFIGS.keys(),
        required=True,
        help=f"Specify the model type to use. Options: {', '.join(MODEL_CONFIGS.keys())}"
    )
    args = parser.parse_args()

    selected_config = MODEL_CONFIGS.get(args.model)
    if not selected_config:
        print(f"Error: Unsupported model type '{args.model}'.")
        exit(1)
    
    selected_model_name = selected_config["model_name"]
    selected_annotations_file = os.path.join(ANNOTATIONS_DIR, selected_config["annotations_file"])

    if not OPENAI_API_KEY or "YOUR_OPENROUTER_API_KEY_HERE" in OPENAI_API_KEY:
        print("Error: Please replace 'YOUR_OPENROUTER_API_KEY_HERE' with your actual OpenRouter API key in auto_annotate_merged.py.")
        exit(1)
    else:
        client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENAI_API_KEY,
        )
        print(f"Starting AI performance annotation process (Model: {selected_model_name}, Annotation File: {selected_annotations_file})...")
        annotations = load_annotations(selected_annotations_file)
        
        app_dirs = [d for d in os.listdir(IMAGE_DATA_ROOT) if os.path.isdir(os.path.join(IMAGE_DATA_ROOT, d))]
        for app_name in app_dirs:
            sample_ids = set(f.split('__')[0] for f in os.listdir(os.path.join(IMAGE_DATA_ROOT, app_name)) if f.lower().endswith('.png'))
            for sample_id in sorted(list(sample_ids)):
                if 'ai' in annotations.get(app_name, {}).get(sample_id, {}) :
                    print(f"Skipping {app_name}/{sample_id}: Already has AI annotation result for model {annotations[app_name][sample_id]['ai'].get('model_used')}.")
                    continue
                
                ai_result = annotate_sample_with_ai(client, app_name, sample_id, selected_model_name)
                if ai_result:
                    annotations[app_name][sample_id]['ai'] = ai_result
                    save_annotations(annotations, selected_annotations_file)
                time.sleep(1) # Keep a short delay to avoid rate limiting
        print("\nAI performance annotation process finished.")