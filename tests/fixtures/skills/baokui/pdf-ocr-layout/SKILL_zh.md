---
name: pdf-ocr-layout
description: 基于智谱 GLM-OCR、GLM-4.7 及 GLM-4.6V 的多模态文档深度解析工具。

  Use when:
  - 需要高精度提取文档（PDF/图片）中的表格并转换为 Markdown 格式
  - 需要从文档页面中自动裁剪并提取插图、图表为独立文件
  - 需要对提取的图表进行深度语义理解（基于 GLM-4.6V 视觉分析）
  - 需要对提取的表格数据进行逻辑分析（基于 GLM-4.7 文本分析）

  核心架构：
  1. 视觉提取：GLM-OCR
  2. 语义理解：GLM-4.7 (纯文本/表格) + GLM-4.6V (多模态/图像)
---

# GLM-OCR 多模态深度解析 (Multimodal Layout Analysis)

本工具构建了一个高精度的文档解析流水线：利用 **GLM-OCR** 进行版面要素提取，针对表格数据调用 **GLM-4.7** 进行逻辑解读，针对图像图表调用 **GLM-4.6V** 进行多模态视觉解读。

## 流水线实现架构 (Pipeline Architecture)

本 Skill 由两个核心脚本阶段组成，通过 `glm_ocr_pipeline.py` 进行统筹调用：

### 1. 提取阶段 (`scripts/glm_ocr_extract.py`)

- **核心模型**: GLM-OCR
- **功能**: 负责文档的物理版面分析
- **产出**: 提取表格 HTML 并清洗为 Markdown，根据 Bbox 坐标自动裁剪出独立的图表图片文件，并生成包含整页阅读顺序的中间态 JSON

### 2. 理解阶段 (`scripts/glm_understanding.py`)

- **核心模型**: GLM-4.7 (文本) / GLM-4.6V (视觉)
- **功能**: 负责内容的深度语义推理
- **逻辑**:
  - **表格**: 结合全文上下文，使用 GLM-4.7 分析 Markdown 表格数据的业务含义
  - **图表**: 结合全文上下文 + 裁剪后的图片，使用 GLM-4.6V 进行多模态视觉分析

## 调用方式

### 命令行调用

```bash
# 运行完整流水线：提取 -> 裁剪 -> 理解分析，支持输入 .pdf, .jpg, .png 等格式
python scripts/glm_ocr_pipeline.py \
  --file_path "/data/report_page.jpg" \
  --output_dir "/data/output"
```

## API 参数说明

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| file_path | string | ✅ | 输入文件绝对路径 (支持 .pdf, .png, .jpg) |
| output_dir | string | ✅ | 结果输出目录 (用于保存裁剪图片和 JSON 报告) |

## 返回结果结构 (JSON)

工具返回包含版面元素及其深度理解的列表：

```json
[
  {
    "type": "table",
    "bbox": [100, 200, 500, 600],
    "content_info": "| Revenue | Q1 |\n|---|---|\n| 100M | ... |",
    "deep_understanding": "（由 GLM-4.7 生成）该表格展示了2024年Q1的营收数据。结合正文第3段提到的'市场扩张策略'，可以看出..."
  },
  {
    "type": "image",
    "bbox": [100, 700, 500, 900],
    "content_info": "/data/output/images/report_page_img_2.png",
    "deep_understanding": "（由 GLM-4.6V 生成）这是一张系统架构图。视觉上展示了客户端通过 Load Balancer 连接服务器的流程。结合标题 'Fig 3' 和上下文，这张图主要用于说明..."
  }
]
```

## 环境要求

- 环境变量 `ZHIPU_API_KEY` 必须已配置
- Python 3.8+
- 依赖库：`zhipuai`, `pillow`, `beautifulsoup4`

## 注意事项

### 1. 模型分流策略

- **Table (表格)**: 内容传入 **GLM-4.7**，结合全文 Markdown 上下文进行逻辑推理
- **Image (图片)**: 图片 Base64 编码传入 **GLM-4.6V**，结合 OCR 提取的标题和全文上下文进行多模态理解

### 2. 上下文关联

所有理解均基于文档的完整版面逻辑（Markdown Context），而非孤立的片段分析。

### 3. PDF 处理

多页 PDF 默认处理首页，如需批量处理请在脚本层扩展循环逻辑。
