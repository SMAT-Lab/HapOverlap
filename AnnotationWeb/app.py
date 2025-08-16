# app.py (为新UI重构标签定义)
import os, json, natsort
from flask import Flask, render_template, request, jsonify, send_from_directory
from collections import defaultdict

APP_ROOT = os.path.dirname(os.path.abspath(__file__))
IMAGE_DATA_DIR = os.path.join(APP_ROOT, "overlap_visualizations_3_sampled_complete")
# ANNOTATIONS_FILE = "annotations.json"
ANNOTATIONS_FILE = "anno_human_ai/gemini.json"
ITEMS_PER_PAGE = 1

# --- ###################### 核心修改: 为新UI设计的标签结构 ###################### ---
# 我们将两组标签的定义分开，并给予清晰的标题
# 注意：两个组的选项是完全相同的，只是用于UI的不同部分
LABEL_OPTIONS = [
    {
        "id": "高成本渲染组件遮挡", 
        "title": "高成本渲染组件遮挡", 
        "description": "当一个高成本组件（如视频、地图、动画等）被另一个UI元素显著遮挡时选择此项。"
    },
    {
        "id": "非高成本渲染组件遮挡", 
        "title": "非高成本渲染组件遮挡", 
        "description": "当发生的遮挡不涉及任何高成本组件时选择此项（例如：角标盖在静态图片上，Toast提示等）。"
    }
]

LABELS = {
    "ai_choice": {
        "title": "AI 标注结果 (只读)",
        "options": LABEL_OPTIONS
    },
    "human_choice": {
        "title": "您的人工确认",
        "options": LABEL_OPTIONS
    }
}
# --- ############################## 修改结束 ############################## ---


app = Flask(__name__)

def deep_defaultdict(): return defaultdict(deep_defaultdict)

def load_annotations():
    if not os.path.exists(ANNOTATIONS_FILE): return deep_defaultdict()
    try:
        with open(ANNOTATIONS_FILE, 'r', encoding='utf-8') as f: data = json.load(f)
        annotations = deep_defaultdict()
        for app, samples in data.items():
            for sample_id, annos in samples.items():
                if isinstance(annos, dict):
                    if 'ai' in annos or 'human' in annos: annotations[app][sample_id].update(annos)
                    elif 'label_problem_exists' in annos: annotations[app][sample_id]['human'] = annos
                    else: annotations[app][sample_id]['human'] = annos
                elif isinstance(annos, str):
                    annotations[app][sample_id]['human'] = {"label": annos, "annotator": "Human"}
        return annotations
    except (FileNotFoundError, json.JSONDecodeError): return deep_defaultdict()

def save_annotations(data):
    def convert_to_dict(item):
        if isinstance(item, defaultdict): return {k: convert_to_dict(v) for k, v in item.items()}
        return item
    regular_dict = convert_to_dict(data)
    with open(ANNOTATIONS_FILE, 'w', encoding='utf-8') as f: json.dump(regular_dict, f, indent=4, ensure_ascii=False)

def scan_image_data(root_dir):
    if not os.path.exists(root_dir): print(f"错误: 图片目录 '{root_dir}' 不存在。"); return {}, []
    structured_data = defaultdict(lambda: defaultdict(dict))
    app_names = natsort.natsorted([d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))])
    for app_name in app_names:
        app_path = os.path.join(root_dir, app_name)
        files = natsort.natsorted(os.listdir(app_path))
        for filename in files:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                try: sample_id = filename.split('__')[0]
                except IndexError: continue
                relative_path = os.path.join(app_name, filename).replace(os.sep, '/')
                if '__before' in filename: structured_data[app_name][sample_id]['before'] = relative_path
                elif '__current' in filename: structured_data[app_name][sample_id]['current'] = relative_path
                elif '__after' in filename: structured_data[app_name][sample_id]['after'] = relative_path
    final_data = {}
    for app_name, samples in structured_data.items():
        sorted_samples = sorted(samples.items(), key=lambda item: natsort.natsorted(item[0]))
        final_data[app_name] = [{"id": sid, "images": s_data} for sid, s_data in sorted_samples]
    return final_data, app_names

ALL_IMAGE_DATA, ALL_APP_NAMES = scan_image_data(IMAGE_DATA_DIR)
TOTAL_APPS = len(ALL_APP_NAMES)

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    if page < 1: page = 1
    if page > TOTAL_APPS and TOTAL_APPS > 0: page = TOTAL_APPS
    start_index = (page - 1) * ITEMS_PER_PAGE
    current_app_name = ALL_APP_NAMES[start_index] if start_index < TOTAL_APPS else None
    samples_for_app = ALL_IMAGE_DATA.get(current_app_name, [])
    annotations = load_annotations()
    return render_template('index.html', app_name=current_app_name, samples=samples_for_app, labels=LABELS, annotations=annotations.get(current_app_name, {}), current_page=page, total_pages=TOTAL_APPS)

@app.route('/annotate', methods=['POST'])
def annotate():
    data = request.get_json()
    if not all(k in data for k in ['app_name', 'sample_id', 'label']): 
        return jsonify({"status": "error", "message": "Missing data"}), 400
    
    app_name, sample_id, label = data['app_name'], data['sample_id'], data['label']
    
    annotations = load_annotations()
    annotations[app_name][sample_id]['human'] = {"label": label, "annotator": "Human"}
    save_annotations(annotations)
    return jsonify({"status": "success", "message": "Annotation saved."})


@app.route('/images/<path:filepath>')
def serve_image(filepath): return send_from_directory(IMAGE_DATA_DIR, filepath)

if __name__ == '__main__':
    if not os.path.exists(IMAGE_DATA_DIR): print(f"警告: 图片目录 '{IMAGE_DATA_DIR}' 不存在。")
    app.run(host='0.0.0.0', port=5005, debug=True)