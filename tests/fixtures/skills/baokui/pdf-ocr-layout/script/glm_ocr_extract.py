import os
import json
import base64
import argparse
from pathlib import Path
from bs4 import BeautifulSoup
from PIL import Image, ImageOps
from zai import ZhipuAiClient

# 初始化客户端
client = ZhipuAiClient(api_key=os.getenv("ZHIPU_API_KEY"))



def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:image/png;base64,{encoded}"

def html_to_markdown(html_content):
    """将HTML表格转为Markdown，方便LLM阅读"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        rows = soup.find_all('tr')
        md_lines = []
        for i, row in enumerate(rows):
            cols = row.find_all(['td', 'th'])
            col_texts = [ele.get_text(strip=True).replace('\n', ' ') for ele in cols]
            if not col_texts: continue
            md_lines.append("| " + " | ".join(col_texts) + " |")
            if i == 0: # 假设第一行是表头
                md_lines.append("| " + " | ".join(["---"] * len(col_texts)) + " |")
        return "\n".join(md_lines)
    except:
        return html_content

def get_nearest_title(target_bbox, all_details, page_h):
    """几何算法：寻找距离最近的 figure_title 或 table_title"""
    target_cy = (target_bbox[1] + target_bbox[3]) / 2
    nearest_title = None
    min_dist = page_h * 0.15 # 搜索范围阈值

    for item in all_details:
        # 确保 item 是对象或字典，兼容 LayoutDetail 对象访问
        label = item.native_label if hasattr(item, 'native_label') else item.get('native_label')
        bbox = item.bbox_2d if hasattr(item, 'bbox_2d') else item.get('bbox_2d')
        content = item.content if hasattr(item, 'content') else item.get('content')

        if label in ['figure_title', 'table_title']:
            item_cy = (bbox[1] + bbox[3]) / 2
            dist = abs(target_cy - item_cy)
            if dist < min_dist:
                min_dist = dist
                # 清洗 HTML 标签
                clean_content = BeautifulSoup(content, 'html.parser').get_text(strip=True)
                nearest_title = clean_content
    return nearest_title

def process_file(file_path, output_dir):
    file_path = Path(file_path).resolve()
    output_dir = Path(output_dir).resolve()
    img_dir = output_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    print(f"[OCR] Processing {file_path.name}...")

    print(file_path)
    # 1. 调用 GLM-OCR
    response = client.layout_parsing.create(
        model="glm-ocr",
        file=image_to_base64(file_path)
    )

    # 2. 准备图片裁剪
    try:
        original_img = Image.open(file_path)
        original_img = ImageOps.exif_transpose(original_img)
        # 计算缩放比例 (API返回的坐标基于 data_info.pages[0] 的尺寸)
        page_w = response.data_info.pages[0].width
        page_h = response.data_info.pages[0].height
        scale_x = original_img.width / page_w
        scale_y = original_img.height / page_h
    except Exception as e:
        print(f"[Warn] Cannot load image for cropping: {e}")
        original_img = None
        scale_x, scale_y = 1, 1

    extracted_elements = []
    
    # 3. 提取关键信息
    # md_results 是理解上下文的核心，必须保存
    full_context_md = response.md_results 

    print(response)
    for idx, item in enumerate(response.layout_details[0]):
        if item.label not in ['image', 'table']:
            continue

        element_data = {
            "id": f"{item.label}_{idx}",
            "type": item.label,
            "bbox": item.bbox_2d,
            "detected_title": get_nearest_title(item.bbox_2d, response.layout_details[0], page_h)
        }

        # 处理表格
        if item.label == 'table':
            element_data["content"] = html_to_markdown(item.content)
            element_data["file_path"] = None # 表格不需要保存图片，除非你想

        # 处理图片
        elif item.label == 'image':
            element_data["content"] = "[Image File]"
            if original_img:
                x1, y1, x2, y2 = item.bbox_2d
                crop = original_img.crop((x1*scale_x, y1*scale_y, x2*scale_x, y2*scale_y))
                save_name = f"{file_path.stem}_{item.label}_{idx}.png"
                save_path = img_dir / save_name
                crop.save(save_path)
                element_data["file_path"] = str(save_path)
            else:
                element_data["file_path"] = None

        extracted_elements.append(element_data)

    # 4. 生成中间态数据包 (Payload for Script 2)
    payload = {
        "source_file": str(file_path),
        "full_markdown_context": full_context_md, # 核心：整页的阅读逻辑文本
        "elements": extracted_elements
    }

    json_path = output_dir / f"{file_path.stem}_data.json"
    with open(json_path, "w", encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    
    print(f"[OCR] Done. Data saved to {json_path}")
    return str(json_path)

if __name__ == "__main__":
    # 示例调用
    parser = argparse.ArgumentParser(description="Zhipu GLM-OCR Layout Parser")
    parser.add_argument("--file", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    process_file(args.file, args.out)