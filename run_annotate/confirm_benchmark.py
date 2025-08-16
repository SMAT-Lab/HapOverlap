import json
import os

# 定义输入和输出文件路径
INPUT_FILE = 'Benchmark/benchmark_full.json'
OUTPUT_FILE = 'Benchmark/benchmark_false.json'

def filter_benchmark_data(input_path, output_path):
    """
    筛选 benchmark_full.json 中 AI 标注数量 >= 2 且 human 为 false 的样本。

    Args:
        input_path (str): 输入 JSON 文件的路径 (benchmark_full.json)。
        output_path (str): 输出 JSON 文件的路径 (benchmark_false.json)。
    """
    filtered_data = {}

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"错误: 未找到文件 {input_path}。请确保文件存在。")
        return
    except json.JSONDecodeError:
        print(f"错误: 文件 {input_path} 不是有效的 JSON 格式。")
        return

    count_filtered_samples = 0

    for app, samples in data.items():
        for sample_name, info in samples.items():
            ai_labels = info.get('ai')
            human_label = info.get('human')

            # 检查条件：ai 必须是列表且长度 >= 2，同时 human 必须为 false
            if isinstance(ai_labels, list) and len(ai_labels) >= 2 and human_label is False:
                filtered_data.setdefault(app, {})[sample_name] = info
                count_filtered_samples += 1

    # 将筛选后的数据写入新文件
    with open(output_path, 'w', encoding='utf-8') as f:
        # json.dump(filtered_data, f, ensure_ascii=False, indent=2)
        json.dump(filtered_data, f, ensure_ascii=False, indent=2, sort_keys=True)

    print(f"已处理文件: {input_path}")
    print(f"共筛选出 {count_filtered_samples} 个符合条件的样本。")
    print(f"筛选结果已保存到: {output_path}")

if __name__ == "__main__":
    filter_benchmark_data(INPUT_FILE, OUTPUT_FILE)