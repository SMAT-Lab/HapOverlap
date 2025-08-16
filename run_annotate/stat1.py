import os
import json

def count_annotations_in_dir(directory):
    stats = {}
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        count = len(data)
                    elif isinstance(data, dict):
                        count = len(data)
                    else:
                        count = 0
                stats[filename] = count
            except Exception as e:
                stats[filename] = f"Error: {e}"
    return stats

if __name__ == "__main__":
    directory = "annotations_2"
    stats = count_annotations_in_dir(directory)
    print(f"统计目录 {directory} 下的 JSON 文件条目数：")
    for fname, count in stats.items():
        print(f"{fname}: {count}")