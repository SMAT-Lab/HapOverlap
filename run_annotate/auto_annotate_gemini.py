# auto_annotate.py (包含Solution的最终版)

import os
import json
import time
import glob
from collections import defaultdict
from google import genai
from google.genai import types

# --- 配置 (Google Gemini) ---
GOOGLE_API_KEY = "YOUR_GOOGLE_AI_API_KEY_HERE"

# --- 常量 ---
IMAGE_DATA_ROOT = "overlap_visualizations_3_sampled_complete"
ANNOTATIONS_FILE = "annotations_gemini_1.json"
# MODEL_NAME = "gemini-2.5-flash"
DEL_NAME = "gemini-2.5-flash-preview-04-17"

# --- ###################### 核心修改: 全新的PROMPT定义，增加Solution要求 ###################### ---
PROMPT_INSTRUCTIONS = """
你是一位顶级的移动应用性能优化专家和资深Android/iOS工程师。

### 你的核心任务:
分析给定的三张UI截图，判断在核心的 `current` 图片中，是否发生了“一个高成本组件被显著遮挡”的性能问题，并提供具体的代码级优化建议。

### “高成本组件”的定义 (关键判断依据):
1.  **重渲染型**: 视频播放器(Video Player)、复杂动画(Animation)、地图(Map)、相机预览(Camera Preview)。
2.  **重计算/IO型**: 复杂图表(Complex Chart)、数据密集型列表(Data-Heavy List)。

### “被显著遮挡”的定义:
指一个其他UI元素（例如：弹窗、底部菜单(ActionSheet)、广告、另一个卡片）覆盖在了“高成本组件”之上，导致其大部分或全部内容对用户不可见或不可交互。

### 你的分析流程:
1.  **识别**: 首先，仔细检查 `current` 图片，判断其中是否存在“高成本组件”。
2.  **判断**:
    *   如果**不存在**任何“高成本组件”，结论就是**“否 (No)”**。
    *   如果**存在**一个或多个“高成本组件”，接着判断它是否**被显著遮挡**。
    *   如果被遮挡，结论为**“是 (Yes)”**。
    *   如果未被遮挡，或遮挡物非常小，则结论为**“否 (No)”**。
3.  **忽略截图瑕疵**: 如果图片边缘有内容被生硬截断，这是截图工具的问题，**不是遮挡**，应忽略。

### 输出要求:
你的回答 **必须** 是一个单一、有效的JSON对象，不包含任何其他解释性文字或Markdown标记。JSON对象必须只包含三个键:
1.  `"label"`: 字符串，值必须是 `"Yes"` 或 `"No"`。
2.  `"reason"`: 一句简明扼要的中文解释，说明你的判断依据。
    *   如果为`Yes`，原因需说明**“什么高成本组件被什么东西遮挡了”** (例如: "视频播放器被一个登录弹窗遮挡")。
    *   如果为`No`，原因需说明**“未发现高成本组件”**或**“高成本组件（如地图）存在但并未被遮挡”**。
3.  `"solution"`: 字符串，提供具体的、可操作的优化建议。
    *   如果`label`为`Yes`，提供代码级的优化建议 (例如: "当弹窗出现时，通过调用 `videoView.pause()` 暂停视频渲染，并在弹窗关闭后调用 `videoView.resume()` 恢复。或在RecyclerView中，通过 `onViewDetachedFromWindow` 回调来释放被遮挡的视频资源。")。
    *   如果`label`为`No`，`solution`的值应为 "无需优化"。
"""
# --- ############################## PROMPT修改结束 ############################## ---


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

def find_image_paths(app_name, sample_id):
    paths = {};
    for state in ['before', 'current', 'after']:
        pattern = os.path.join(IMAGE_DATA_ROOT, app_name, f"{sample_id}__{state}*.png")
        found_files = glob.glob(pattern);
        if found_files: paths[state] = found_files[0]
        else: paths[state] = None

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

    return paths

def annotate_sample_with_ai(client, app_name, sample_id):
    print(f"正在处理: {app_name} / {sample_id}")
    image_paths = find_image_paths(app_name, sample_id)
    if not all(image_paths.values()): print(f"  -> 跳过: 未能找到全部三张图片。"); return None

    image_parts = []
    try:
        # 1. 'before' image
        with open(image_paths['before'], 'rb') as f:
            image_bytes_before = f.read()
        image_parts.append(types.Part.from_bytes(data=image_bytes_before, mime_type='image/png'))

        # 2. 'current' image
        with open(image_paths['current'], 'rb') as f:
            image_bytes_current = f.read()
        image_parts.append(types.Part.from_bytes(data=image_bytes_current, mime_type='image/png'))

        # 3. 'after' image
        with open(image_paths['after'], 'rb') as f:
            image_bytes_after = f.read()
        image_parts.append(types.Part.from_bytes(data=image_bytes_after, mime_type='image/png'))

    except IOError as e:
        print(f"  -> 跳过: 读取图片文件时出错。错误: {e}")
        return None

    contents = [image_parts[0], image_parts[1], image_parts[2], PROMPT_INSTRUCTIONS]

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents
        )
        raw_text = response.text
        first_brace, last_brace = raw_text.find('{'), raw_text.rfind('}')
        if first_brace == -1 or last_brace == -1:
            print(f"  -> JSON 解析错误: 模型响应中未找到有效的JSON结构。响应: {raw_text}"); return None
        json_str = raw_text[first_brace : last_brace + 1]
        result = json.loads(json_str)

        if 'label' in result and 'reason' in result and 'solution' in result and result['label'] in ['Yes', 'No']:
            print(f"  -> 成功: AI分类为 {result['label']}。")
            result['annotator'] = 'AI'
            result['model_used'] = MODEL_NAME
            result['annotation_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
            return result
        else:
            print(f"  -> 解析错误: AI响应的JSON无效或缺少键。响应: {response.text}"); return None
            
    except json.JSONDecodeError as e:
        print(f"  -> JSON 解析错误: 无法解析提取出的字符串。错误: {e}。提取内容: '{json_str}'"); return None
    except Exception as e:
        print(f"  -> Gemini API 或其他未知错误: {e}")
        if 'response' in locals() and hasattr(response, 'prompt_feedback'): print(f"  -> Prompt Feedback: {response.prompt_feedback}")
        return None

if __name__ == "__main__":
    if not GOOGLE_API_KEY or "YOUR_GOOGLE_AI_API_KEY_HERE" in GOOGLE_API_KEY:
        print("错误: 请在auto_annotate.py文件中将 'YOUR_GOOGLE_AI_API_KEY_HERE' 替换为您的真实Google AI API密钥。")
    else:
        client = genai.Client(api_key=GOOGLE_API_KEY)
        print("开始AI性能标注流程 (包含解决方案)...")
        annotations = load_annotations()
        app_dirs = [d for d in os.listdir(IMAGE_DATA_ROOT) if os.path.isdir(os.path.join(IMAGE_DATA_ROOT, d))]
        for app_name in app_dirs:
            sample_ids = set(f.split('__')[0] for f in os.listdir(os.path.join(IMAGE_DATA_ROOT, app_name)) if f.lower().endswith('.png'))
            for sample_id in sorted(list(sample_ids)):
                if 'ai' in annotations.get(app_name, {}).get(sample_id, {}):
                    print(f"跳过 {app_name}/{sample_id}: 已有AI标注结果。")
                    continue
                ai_result = annotate_sample_with_ai(client, app_name, sample_id)
                if ai_result:
                    annotations[app_name][sample_id]['ai'] = ai_result
                    save_annotations(annotations)
                time.sleep(2) 
        print("\nAI性能标注流程结束。")