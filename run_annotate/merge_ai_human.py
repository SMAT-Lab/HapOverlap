import json
import os

# 输入文件路径
HUMAN_ANNOTATIONS_PATH = 'gt2.json'
# AI 模型注释文件所在的目录
AI_ANNOTATIONS_DIR = './annotations_2'
# 输出合并结果的目录
OUTPUT_MERGED_DIR = './anno_human_ai_2'

# 确保输出目录存在
os.makedirs(OUTPUT_MERGED_DIR, exist_ok=True)

# 读取 human 文件
def load_human_annotations(file_path):
    """
    加载人类标注文件，并提取 'human' 字段的数据。
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        result = {}
        for app, samples in data.items():
            for sample, info in samples.items():
                if isinstance(info, dict) and 'human' in info:
                    result.setdefault(app, {})[sample] = {'human': info['human']}
        print(f"成功加载人类标注文件: {file_path}")
        return result
    except FileNotFoundError:
        print(f"错误: 未找到人类标注文件 {file_path}。")
        return None
    except json.JSONDecodeError:
        print(f"错误: 人类标注文件 {file_path} 不是有效的 JSON 格式。")
        return None

# 读取 AI 文件
def load_ai_annotations(file_path):
    """
    加载 AI 标注文件，并提取 'ai' 字段的数据。
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        result = {}
        for app, samples in data.items():
            for sample, info in samples.items():
                if isinstance(info, dict) and 'ai' in info:
                    result.setdefault(app, {})[sample] = {'ai': info['ai']}
        print(f"成功加载 AI 标注文件: {file_path}")
        return result
    except FileNotFoundError:
        print(f"错误: 未找到 AI 标注文件 {file_path}。")
        return None
    except json.JSONDecodeError:
        print(f"错误: AI 标注文件 {file_path} 不是有效的 JSON 格式。")
        return None

# 合并 human 和 AI 数据
def merge_annotations(human_dict, ai_dict):
    """
    合并人类标注和 AI 标注数据。
    """
    if human_dict is None or ai_dict is None:
        return None

    merged = {}
    # 获取所有 app 名称（human 和 AI 数据中的并集）
    apps = set(human_dict.keys()) | set(ai_dict.keys())

    for app in apps:
        # 获取当前 app 下的所有 sample 名称
        samples = set(human_dict.get(app, {}).keys()) | set(ai_dict.get(app, {}).keys())
        for sample in samples:
            merged.setdefault(app, {})[sample] = {}
            # 如果 human 数据中存在，则添加 human 标注
            if app in human_dict and sample in human_dict[app]:
                merged[app][sample].update(human_dict[app][sample])
            # 如果 AI 数据中存在，则添加 AI 标注
            if app in ai_dict and sample in ai_dict[app]:
                merged[app][sample].update(ai_dict[app][sample])
    return merged

def process_model_annotations(model_file_name, human_annotations):
    """
    处理单个 AI 模型文件，并将其与人类标注合并。
    Args:
        model_file_name (str): AI 模型注释文件名，例如 'annotations_llama.json'。
        human_annotations (dict): 预先加载的人类标注数据。
    """
    model_name = model_file_name.replace('annotations_', '').replace('.json', '')
    ai_input_path = os.path.join(AI_ANNOTATIONS_DIR, model_file_name)
    output_path = os.path.join(OUTPUT_MERGED_DIR, f'{model_name}.json')

    print(f"\n--- 正在处理 {model_name} 模型数据 ---")

    ai_dict = load_ai_annotations(ai_input_path)
    if ai_dict is None:
        print(f"跳过 {model_name} 的合并，因为 AI 标注加载失败。")
        return

    merged_data = merge_annotations(human_annotations, ai_dict)

    if merged_data is None:
        print(f"跳过 {model_name} 的合并，因为合并操作失败。")
        return

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"已输出合并结果到 {output_path}")
    print(f"--- {model_name} 模型数据处理完成 ---\n")

if __name__ == "__main__":
    # 预加载人类标注数据，因为它是所有合并的基础
    human_data = load_human_annotations(HUMAN_ANNOTATIONS_PATH)

    if human_data is None:
        print("无法加载人类标注数据，程序将退出。")
    else:
        # 定义需要处理的 AI 模型文件列表
        # 您可以根据实际的 AI 标注文件名进行扩展
        ai_model_files = [
            'annotations_llama.json',
            'annotations_qwen.json',
            'annotations_openai.json',
            'annotations_gemini.json', # 假设您也有gemini的annotations_2/annotations_gemini.json
            # 添加更多 AI 模型的文件名
        ]

        for ai_file in ai_model_files:
            process_model_annotations(ai_file, human_data)

    print("\n所有指定模型的合并处理已完成。")