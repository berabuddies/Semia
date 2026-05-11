---
name: md-to-office
description: Convert Markdown to Word, PowerPoint, and PDF using Pandoc - the universal document converter
author: claude-office-skills
version: "1.0"
tags: [markdown, conversion, pandoc, word, pdf, powerpoint]
models: [claude-sonnet-4, claude-opus-4]
tools: [computer, code_execution, file_operations]
library:
  name: pandoc
  url: https://github.com/jgm/pandoc
  stars: 42k
---

# Markdown to Office Skill

## Overview

This skill enables conversion from Markdown to various Office formats using **Pandoc** - the universal document converter. Convert your Markdown files to professional Word documents, PowerPoint presentations, PDFs, and more while preserving formatting and structure.

## How to Use

1. Provide the Markdown content or file
2. Specify the target format (docx, pptx, pdf, etc.)
3. Optionally provide a reference template for styling
4. I'll convert using Pandoc with optimal settings

**Example prompts:**
- "Convert this README.md to a professional Word document"
- "Turn my markdown notes into a PowerPoint presentation"
- "Generate a PDF from this markdown with custom styling"
- "Create a Word doc from this markdown using company template"

## Domain Knowledge

### Pandoc Fundamentals

```bash
# Basic conversion
pandoc input.md -o output.docx
pandoc input.md -o output.pdf
pandoc input.md -o output.pptx

# With template
pandoc input.md --reference-doc=template.docx -o output.docx

# Multiple inputs
pandoc ch1.md ch2.md ch3.md -o book.docx
```

### Supported Conversions

| From | To | Command |
|------|-----|---------|
| Markdown | Word | `pandoc in.md -o out.docx` |
| Markdown | PDF | `pandoc in.md -o out.pdf` |
| Markdown | PowerPoint | `pandoc in.md -o out.pptx` |
| Markdown | HTML | `pandoc in.md -o out.html` |
| Markdown | LaTeX | `pandoc in.md -o out.tex` |
| Markdown | EPUB | `pandoc in.md -o out.epub` |

### Markdown to Word (.docx)

#### Basic Conversion
```bash
pandoc document.md -o document.docx
```

#### With Template (Reference Doc)
```bash
# First create a template by converting sample
pandoc sample.md -o reference.docx

# Edit reference.docx styles in Word, then use it
pandoc input.md --reference-doc=reference.docx -o output.docx
```

#### With Table of Contents
```bash
pandoc document.md --toc --toc-depth=3 -o document.docx
```

#### With Metadata
```bash
pandoc document.md \
  --metadata title="My Report" \
  --metadata author="John Doe" \
  --metadata date="2024-01-15" \
  -o document.docx
```

### Markdown to PDF

#### Via LaTeX (Best Quality)
```bash
# Requires LaTeX installation
pandoc document.md -o document.pdf

# With custom settings
pandoc document.md \
  --pdf-engine=xelatex \
  -V geometry:margin=1in \
  -V fontsize=12pt \
  -o document.pdf
```

#### Via HTML/wkhtmltopdf
```bash
pandoc document.md \
  --pdf-engine=wkhtmltopdf \
  --css=style.css \
  -o document.pdf
```

#### PDF Options
```bash
pandoc document.md \
  -V papersize:a4 \
  -V geometry:margin=2cm \
  -V fontfamily:libertinus \
  -V colorlinks:true \
  --toc \
  -o document.pdf
```

### Markdown to PowerPoint (.pptx)

#### Basic Conversion
```bash
pandoc slides.md -o presentation.pptx
```

#### Markdown Structure for Slides
```markdown
---
title: Presentation Title
author: Author Name
date: January 2024
---

# Section Header (creates section divider)

## Slide Title

- Bullet point 1
- Bullet point 2
  - Sub-bullet

## Another Slide

Content here

::: notes
Speaker notes go here (not visible in slides)
:::

## Slide with Image

![Description](image.png){width=80%}

## Two Column Slide

:::::::::::::: {.columns}
::: {.column width="50%"}
Left column content
:::

::: {.column width="50%"}
Right column content
:::
::::::::::::::
```

#### With Template
```bash
# Use corporate PowerPoint template
pandoc slides.md --reference-doc=template.pptx -o presentation.pptx
```

### YAML Frontmatter

Add metadata at the top of your Markdown:

```yaml
---
title: "Document Title"
author: "Author Name"
date: "2024-01-15"
abstract: "Brief description"
toc: true
toc-depth: 2
numbersections: true
geometry: margin=1in
fontsize: 11pt
documentclass: report
---

# First Chapter
...
```

### Python Integration

```python
import subprocess
import os

def md_to_docx(input_path, output_path, template=None):
    """Convert Markdown to Word document."""
    cmd = ['pandoc', input_path, '-o', output_path]
    
    if template:
        cmd.extend(['--reference-doc', template])
    
    subprocess.run(cmd, check=True)
    return output_path

def md_to_pdf(input_path, output_path, **options):
    """Convert Markdown to PDF with options."""
    cmd = ['pandoc', input_path, '-o', output_path]
    
    if options.get('toc'):
        cmd.append('--toc')
    
    if options.get('margin'):
        cmd.extend(['-V', f"geometry:margin={options['margin']}"])
    
    subprocess.run(cmd, check=True)
    return output_path

def md_to_pptx(input_path, output_path, template=None):
    """Convert Markdown to PowerPoint."""
    cmd = ['pandoc', input_path, '-o', output_path]
    
    if template:
        cmd.extend(['--reference-doc', template])
    
    subprocess.run(cmd, check=True)
    return output_path
```

### pypandoc (Python Wrapper)

```python
import pypandoc

# Simple conversion
output = pypandoc.convert_file('input.md', 'docx', outputfile='output.docx')

# With options
output = pypandoc.convert_file(
    'input.md', 
    'docx',
    outputfile='output.docx',
    extra_args=['--toc', '--reference-doc=template.docx']
)

# From string
md_content = "# Hello\n\nThis is markdown."
output = pypandoc.convert_text(md_content, 'docx', format='md', outputfile='output.docx')
```

## Best Practices

1. **Use Templates**: Create a reference document for consistent branding
2. **Structure Headers**: Use consistent heading levels (## for slides, # for sections)
3. **Test Incrementally**: Convert small sections first to verify formatting
4. **Include Metadata**: Use YAML frontmatter for document properties
5. **Handle Images**: Use relative paths and specify dimensions

## Common Patterns

### Batch Conversion
```python
import subprocess
from pathlib import Path

def batch_convert(input_dir, output_format, output_dir=None):
    """Convert all markdown files in a directory."""
    input_path = Path(input_dir)
    output_path = Path(output_dir) if output_dir else input_path
    
    for md_file in input_path.glob('*.md'):
        output_file = output_path / md_file.with_suffix(f'.{output_format}').name
        subprocess.run([
            'pandoc', str(md_file), '-o', str(output_file)
        ], check=True)
        print(f"Converted: {md_file.name} -> {output_file.name}")

batch_convert('./docs', 'docx', './output')
```

### Report Generator
```python
def generate_report(title, sections, output_path, template=None):
    """Generate Word report from structured data."""
    
    # Build markdown
    md_content = f"""---
title: "{title}"
date: "{datetime.now().strftime('%B %d, %Y')}"
---

"""
    for section_title, content in sections.items():
        md_content += f"# {section_title}\n\n{content}\n\n"
    
    # Write temp file
    with open('temp_report.md', 'w') as f:
        f.write(md_content)
    
    # Convert
    cmd = ['pandoc', 'temp_report.md', '-o', output_path, '--toc']
    if template:
        cmd.extend(['--reference-doc', template])
    
    subprocess.run(cmd, check=True)
    os.remove('temp_report.md')
```

## Examples

### Example 1: Technical Documentation
```python
import subprocess

# Create comprehensive markdown
doc = """---
title: "API Documentation"
author: "Dev Team"
date: "2024-01-15"
toc: true
toc-depth: 2
---

# Introduction

This document describes the REST API for our service.

## Authentication

All API requests require an API key in the header:

```
Authorization: Bearer YOUR_API_KEY
```

## Endpoints

### GET /users

Retrieve all users.

**Response:**

| Field | Type | Description |
|-------|------|-------------|
| id | integer | User ID |
| name | string | Full name |
| email | string | Email address |

### POST /users

Create a new user.

**Request Body:**

```json
{
  "name": "John Doe",
  "email": "john@example.com"
}
```

## Error Codes

| Code | Meaning |
|------|---------|
| 400 | Bad Request |
| 401 | Unauthorized |
| 404 | Not Found |
| 500 | Server Error |
"""

# Save markdown
with open('api_docs.md', 'w') as f:
    f.write(doc)

# Convert to Word
subprocess.run([
    'pandoc', 'api_docs.md',
    '-o', 'api_documentation.docx',
    '--toc',
    '--reference-doc', 'company_template.docx'
], check=True)

# Convert to PDF
subprocess.run([
    'pandoc', 'api_docs.md',
    '-o', 'api_documentation.pdf',
    '--toc',
    '-V', 'geometry:margin=1in',
    '-V', 'fontsize=11pt'
], check=True)
```

### Example 2: Presentation from Markdown
```python
slides_md = """---
title: "Q4 Business Review"
author: "Sales Team"
date: "January 2024"
---

# Overview

## Agenda

- Q4 Performance Summary
- Regional Highlights
- 2024 Outlook
- Q&A

# Q4 Performance

## Key Metrics

- Revenue: $12.5M (+15% YoY)
- New Customers: 250
- Retention Rate: 94%

## Regional Performance

:::::::::::::: {.columns}
::: {.column width="50%"}
**North America**

- Revenue: $6.2M
- Growth: +18%
:::

::: {.column width="50%"}
**Europe**

- Revenue: $4.1M
- Growth: +12%
:::
::::::::::::::

# 2024 Outlook

## Strategic Priorities

1. Expand APAC presence
2. Launch new product line
3. Improve customer onboarding

## Revenue Targets

| Quarter | Target |
|---------|--------|
| Q1 | $13M |
| Q2 | $14M |
| Q3 | $15M |
| Q4 | $16M |

# Thank You

## Questions?

Contact: sales@company.com
"""

with open('presentation.md', 'w') as f:
    f.write(slides_md)

subprocess.run([
    'pandoc', 'presentation.md',
    '-o', 'q4_review.pptx',
    '--reference-doc', 'company_slides.pptx'
], check=True)
```

## Limitations

- Complex Word formatting may not convert perfectly
- PDF conversion requires LaTeX or wkhtmltopdf
- PowerPoint animations not supported
- Some advanced tables may need manual adjustment
- Image positioning can be tricky

## Installation

```bash
# macOS
brew install pandoc

# Ubuntu/Debian
sudo apt-get install pandoc

# Windows
choco install pandoc

# Python wrapper
pip install pypandoc
```

## Resources

- [Pandoc User's Guide](https://pandoc.org/MANUAL.html)
- [GitHub Repository](https://github.com/jgm/pandoc)
- [Pandoc Templates](https://github.com/jgm/pandoc-templates)
- [pypandoc Documentation](https://github.com/JessicaTegworthy/pypandoc)
