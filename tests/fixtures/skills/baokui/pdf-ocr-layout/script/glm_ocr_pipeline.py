import argparse
import sys
import json
from pathlib import Path

# 导入刚才写的两个脚本模块
# 假设它们分别命名为 glm_ocr_extract.py 和 glm_understanding.py
# 并且放在同一目录下
from glm_ocr_extract import process_file as run_extraction
from glm_understanding import process_understanding as run_analysis

def main():
    parser = argparse.ArgumentParser(description="GLM-OCR Layout & Understanding Pipeline")
    parser.add_argument("--file_path", required=True, help="Input file path (PDF/Image)")
    parser.add_argument("--output_dir", required=True, help="Directory to save results")
    args = parser.parse_args()

    input_path = Path(args.file_path)
    output_dir = Path(args.output_dir)

    if not input_path.exists():
        print(json.dumps([{"error": f"File not found: {input_path}"}]))
        sys.exit(1)

    try:
        # Step 1: 提取 (OCR + Crop + Markdown)
        # 返回中间态 json 路径
        intermediate_json = run_extraction(str(input_path), str(output_dir))
        
        # Step 2: 理解 (LLM + VLM)
        # 读取中间态 json，生成最终 json，并打印结果
        run_analysis(intermediate_json)

    except Exception as e:
        # 捕获顶层异常，确保输出 JSON 格式错误信息
        print(json.dumps([{"error": f"Pipeline failed: {str(e)}"}], ensure_ascii=False))
        sys.exit(1)

if __name__ == "__main__":
    main()
    