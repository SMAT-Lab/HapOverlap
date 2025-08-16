import json
import os
import re

# Paths
ANNOTATION_PATH = 'anno_human_ai/gemini.json'
BENCHMARK_VIS_ROOT = 'simple_benchmark_vis'
OUTPUT_PATH = 'anno_human_ai_trans/annotations_gemini.json'

def get_img_key(app, sample_id):
    """
    Find the image file in the app's benchmark vis dir for the given sample_id, extract the screenCap_xxx.png part, and return as key.
    """
    app_dir = os.path.join(BENCHMARK_VIS_ROOT, app)
    if not os.path.isdir(app_dir):
        return None
    # List all files for this app
    for fname in os.listdir(app_dir):
        # Match the current sample image file for this sample_id
        # e.g. sample_01__current_sample_01_overlap_vis_screenCap_392252181613.png_1.png
        if fname.startswith(f"{sample_id}__current_") and 'overlap_vis_screenCap_' in fname:
            # Extract screenCap_xxx.png
            m = re.search(r'(screenCap_\d+\.png)', fname)
            if m:
                return m.group(1)
    return None

def main():
    with open(ANNOTATION_PATH, 'r', encoding='utf-8') as f:
        annotations = json.load(f)
    new_dict = {}
    for app, samples in annotations.items():
        new_app_samples = {}
        for sample_id, sample_data in samples.items():
            img_key = get_img_key(app, sample_id)
            if not img_key:
                continue
            # # Only keep 'human' part
            # if 'human' in sample_data:
            #     # new_app_samples[img_key] = sample_data['human']
            #     new_app_samples[img_key] = {'human': sample_data['human']}
            new_app_samples[img_key] = sample_data

        
        if new_app_samples:
            new_dict[app] = new_app_samples

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(new_dict, f, ensure_ascii=False, indent=4)

if __name__ == '__main__':
    main() 