import json
import os

def process_annotations(model_name):
    """
    Processes annotation data from a specified model's JSON file,
    categorizes samples, and outputs them to separate JSON files.

    Args:
        model_name (str): The name of the model (e.g., 'openai', 'gemini').
                          Used to construct input and output paths.
    """
    input_path = f'anno_human_ai_2/{model_name}.json'
    output_dir = f'anno_comp_2/{model_name}'
    os.makedirs(output_dir, exist_ok=True)

    output_both = os.path.join(output_dir, 'both.json')
    output_ai_only = os.path.join(output_dir, 'ai_only.json')
    output_human_only = os.path.join(output_dir, 'human_only.json')

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"错误：未找到文件 {input_path}。请确保路径正确。")
        return
    except json.JSONDecodeError:
        print(f"错误：文件 {input_path} 不是有效的 JSON 格式。")
        return

    both = {}
    ai_only = {}
    human_only = {}

    def count_samples(d):
        return sum(len(samples) for samples in d.values())

    for app, samples in data.items():
        for sample, info in samples.items():
            ai_label = info.get('ai', {}).get('label')
            human_label = info.get('human', {}).get('label')

            # 1. both: ai.label=='Yes' 且 human.label=='高成本渲染组件遮挡'
            if ai_label == 'Yes' and human_label == '高成本渲染组件遮挡':
                both.setdefault(app, {})[sample] = info
            # 2. ai_only: ai.label=='Yes' 且 human.label=='非高成本渲染组件遮挡'
            if ai_label == 'Yes' and human_label == '非高成本渲染组件遮挡':
                ai_only.setdefault(app, {})[sample] = info
            # 3. human_only: human.label=='高成本渲染组件遮挡' 且 ai.label!='Yes'
            if human_label == '高成本渲染组件遮挡' and ai_label != 'Yes':
                human_only.setdefault(app, {})[sample] = info

    with open(output_both, 'w', encoding='utf-8') as f:
        json.dump(both, f, ensure_ascii=False, indent=2)
    with open(output_ai_only, 'w', encoding='utf-8') as f:
        json.dump(ai_only, f, ensure_ascii=False, indent=2)
    with open(output_human_only, 'w', encoding='utf-8') as f:
        json.dump(human_only, f, ensure_ascii=False, indent=2)

    print(f"模型 '{model_name}' 的数据处理完成。")
    print(f"已输出到 {output_both}, {output_ai_only}, {output_human_only}")
    print(f"both 样本数: {count_samples(both)}")
    print(f"ai_only 样本数: {count_samples(ai_only)}")
    print(f"human_only 样本数: {count_samples(human_only)}")
    print("-" * 30)

# 调用函数处理 OpenAI 数据
process_annotations('openai')

# 调用函数处理 Gemini 数据
process_annotations('gemini')

# 如果有更多模型，可以继续调用
process_annotations('qwen')

process_annotations('llama')