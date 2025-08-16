# auto_annotate_merged.py (支持多模型，通过命令行指定)

import os
import json
import time
import glob
import base64
import argparse # 新增：用于命令行参数解析
from collections import defaultdict
from openai import OpenAI

# --- 配置 (OpenAI / OpenRouter) ---
# 请将此处的 YOUR_OPENROUTER_API_KEY_HERE 替换为你的实际 OpenRouter API 密钥
OPENAI_API_KEY = "YOUR_OPENROUTER_API_KEY_HERE"

# 针对OpenRouter.ai的配置
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# --- 常量 ---
IMAGE_DATA_ROOT = "overlap_visualizations_3_sampled_complete"

# --- 模型配置映射 ---
MODEL_CONFIGS = {
    "openai": {
        "model_name": "openai/gpt-4o-mini",
        "annotations_file": "annotations_openai.json" # 为OpenAI模型指定标注文件
    },
    "qwen": {
        "model_name": "qwen/qwen2.5-vl-72b-instruct:free",
        "annotations_file": "annotations_qwen.json" # 为Qwen模型指定标注文件
    },
    "llama": {
        "model_name": "meta-llama/llama-4-maverick",
        "annotations_file": "annotations_llama.json" # 为Llama模型指定标注文件
    },
    "gemini": {
        "model_name": "google/gemini-2.5-flash-preview-05-20:thinking",
        "annotations_file": "annotations_gemini.json" # 为Gemini模型指定标注文件
    }
}

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

# 传入 annotations_file 参数
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

# 传入 annotations_file 参数
def save_annotations(data, annotations_file):
    def convert_to_dict(item):
        if isinstance(item, defaultdict): return {k: convert_to_dict(v) for k, v in item.items()}
        return item
    regular_dict = convert_to_dict(data)
    with open(annotations_file, 'w', encoding='utf-8') as f: json.dump(regular_dict, f, indent=4, ensure_ascii=False)

def find_image_paths(app_name, sample_id):
    paths = {};
    for state in ['before', 'current', 'after']:
        pattern = os.path.join(IMAGE_DATA_ROOT, app_name, f"{sample_id}__{state}*.png")
        found_files = glob.glob(pattern);
        if found_files: paths[state] = found_files[0]
        else: paths[state] = None
    return paths

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# 传入 model_name 参数
def annotate_sample_with_ai(client, app_name, sample_id, model_name):
    print(f"正在处理: {app_name} / {sample_id} (模型: {model_name})")
    image_paths = find_image_paths(app_name, sample_id)
    if not all(image_paths.values()): print(f"  -> 跳过: 未能找到全部三张图片。"); return None

    messages_content = []
    messages_content.append({"type": "text", "text": PROMPT_INSTRUCTIONS})

    try:
        for state in ['before', 'current', 'after']:
            if image_paths[state]:
                base64_image = encode_image(image_paths[state])
                messages_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                })
    except IOError as e:
        print(f"  -> 跳过: 读取图片文件时出错。错误: {e}")
        return None

    try:
        completion = client.chat.completions.create(
            model=model_name, # 使用传入的模型名称
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
            timeout=180.0
        )
        raw_text = completion.choices[0].message.content

        first_brace, last_brace = raw_text.find('{'), raw_text.rfind('}')
        if first_brace == -1 or last_brace == -1:
            print(f"  -> JSON 解析错误: 模型响应中未找到有效的JSON结构。响应: {raw_text}"); return None
        json_str = raw_text[first_brace : last_brace + 1]
        result = json.loads(json_str)

        if 'label' in result and 'reason' in result and 'solution' in result and result['label'] in ['Yes', 'No']:
            print(f"  -> 成功: AI分类为 {result['label']}。")
            result['annotator'] = 'AI'
            result['model_used'] = model_name # 记录使用的模型名称
            result['annotation_timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
            return result
        else:
            print(f"  -> 解析错误: AI响应的JSON无效或缺少键。响应: {raw_text}"); return None
            
    except json.JSONDecodeError as e:
        print(f"  -> JSON 解析错误: 无法解析提取出的字符串。错误: {e}。提取内容: '{json_str}'"); return None
    except Exception as e:
        print(f"  -> API 或其他未知错误: {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="使用OpenRouter API对移动应用UI截图进行性能标注。")
    parser.add_argument(
        "--model",
        type=str,
        choices=MODEL_CONFIGS.keys(),
        required=True,
        help=f"指定要使用的模型类型。可选值: {', '.join(MODEL_CONFIGS.keys())}"
    )
    args = parser.parse_args()

    # 根据命令行参数获取模型配置
    selected_config = MODEL_CONFIGS.get(args.model)
    if not selected_config:
        print(f"错误: 不支持的模型类型 '{args.model}'。")
        exit(1)
    
    selected_model_name = selected_config["model_name"]
    selected_annotations_file = selected_config["annotations_file"]

    if not OPENAI_API_KEY or "YOUR_OPENROUTER_API_KEY_HERE" in OPENAI_API_KEY:
        print("错误: 请在auto_annotate_merged.py文件中将 'YOUR_OPENROUTER_API_KEY_HERE' 替换为您的真实OpenRouter API密钥。")
    else:
        client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENAI_API_KEY,
        )
        print(f"开始AI性能标注流程 (模型: {selected_model_name}, 标注文件: {selected_annotations_file})...")
        annotations = load_annotations(selected_annotations_file) # 传入标注文件路径
        
        app_dirs = [d for d in os.listdir(IMAGE_DATA_ROOT) if os.path.isdir(os.path.join(IMAGE_DATA_ROOT, d))]
        for app_name in app_dirs:
            sample_ids = set(f.split('__')[0] for f in os.listdir(os.path.join(IMAGE_DATA_ROOT, app_name)) if f.lower().endswith('.png'))
            for sample_id in sorted(list(sample_ids)):
                # 检查当前模型是否已经标注过这个样本
                if 'ai' in annotations.get(app_name, {}).get(sample_id, {}) and \
                   annotations[app_name][sample_id]['ai'].get('model_used') == selected_model_name:
                    print(f"跳过 {app_name}/{sample_id}: 已有模型 {selected_model_name} 的AI标注结果。")
                    continue
                
                ai_result = annotate_sample_with_ai(client, app_name, sample_id, selected_model_name) # 传入模型名称
                if ai_result:
                    annotations[app_name][sample_id]['ai'] = ai_result
                    save_annotations(annotations, selected_annotations_file) # 传入标注文件路径
                time.sleep(2) # 保持休眠，避免频繁请求导致API限速
        print("\nAI性能标注流程结束。")