---
name: regex-assistant
description: 正则表达式助手，帮助用户测试、调试和生成正则表达式。支持匹配测试、分组捕获、替换操作等常见正则操作。
---

# 正则表达式助手 (Regex Tester)

正则表达式测试与调试工具，帮助开发者快速验证正则表达式、提取匹配结果和执行替换操作。

## 技能目的

提供便捷的正则表达式测试环境，帮助用户：
- 验证正则表达式是否正确匹配目标文本
- 查看捕获分组的内容
- 执行替换操作并预览结果
- 获取详细的匹配信息

## 何时使用此技能

在以下情况下使用此技能：

- 需要测试或调试正则表达式
- 需要从文本中提取特定模式的内容
- 需要进行批量文本替换
- 需要了解正则表达式的匹配行为
- 需要生成常用正则表达式模式

## 功能特性

### 1. 基本匹配测试

测试正则表达式在目标文本中的匹配情况。

```bash
python3 script/main.py match "<正则>" "<文本>"
```

**示例：**
```bash
# 测试邮箱匹配
python3 script/main.py match "[\w.+-]+@[\w-]+\.[\w.-]+" "contact@example.com"

# 测试手机号匹配（中国大陆）
python3 script/main.py match "1[3-9]\d{9}" "13800138000"
```

### 2. 提取所有匹配

获取文本中所有匹配正则表达式的内容。

```bash
python3 script/main.py findall "<正则>" "<文本>"
```

**示例：**
```bash
# 提取所有URL
python3 script/main.py findall "https?://\S+" "访问 https://example.com 和 http://test.org"

# 提取所有数字
python3 script/main.py findall "\d+" "价格: 99, 数量: 100, 总计: 9900"
```

### 3. 分组捕获

查看正则表达式中的捕获分组内容。

```bash
python3 script/main.py groups "<正则>" "<文本>"
```

**示例：**
```bash
# 解析日志格式
python3 script/main.py groups "\[(.*?)\] \[(.*?)\] (.*)" "[2024-02-14] [INFO] 启动服务"

# 解析日期时间
python3 script/main.py groups "(\d{4})-(\d{2})-(\d{2})" "今天是2024-02-14"
```

### 4. 文本替换

使用正则表达式进行文本替换。

```bash
python3 script/main.py sub "<正则>" "<替换内容>" "<文本>"
```

**示例：**
```bash
# 隐藏手机号中间四位
python3 script/main.py sub "(\d{3})\d{4}(\d{4})" "\1****\2" "联系13800138000"

# 去除HTML标签
python3 script/main.py sub "<[^>]+>" "" "<p>你好<b>世界</b></p>"
```

### 5. 常用模式生成

生成常用场景的正则表达式模式。

```bash
python3 script/main.py pattern "<模式名称>"
```

**支持的模式：**
- `email` - 邮箱地址
- `phone` - 中国手机号
- `idcard` - 中国身份证号
- `ipv4` - IPv4地址
- `url` - URL地址
- `date` - 日期 (YYYY-MM-DD)
- `time` - 时间 (HH:MM:SS)
- `chinese` - 中文字符
- `username` - 用户名 (字母数字下划线)
- `password` - 密码 (至少8位，包含字母和数字)

**示例：**
```bash
python3 script/main.py pattern email
python3 script/main.py pattern phone
```

## 参数说明

| 参数 | 说明 |
|------|------|
| `match` | 测试基本匹配 |
| `findall` | 提取所有匹配 |
| `groups` | 查看分组捕获 |
| `sub` | 执行替换操作 |
| `pattern` | 生成常用模式 |

## 使用示例

### 场景 1: 验证输入格式

```bash
# 验证邮箱格式是否正确
python3 script/main.py match "[\w.+-]+@[\w-]+\.[\w.-]+" "user@company.com"
```

### 场景 2: 提取数据

```bash
# 从日志中提取所有错误代码
python3 script/main.py findall "ERROR:\s*(\w+)" "$(cat error.log)"

# 提取Markdown中的链接
python3 script/main.py findall "\[([^\]]+)\]\(([^)]+)\)" "[首页](https://example.com)"
```

### 场景 3: 数据清洗

```bash
# 统一日期格式
python3 script/main.py sub "(\d{4})/(\d{2})/(\d{2})" "\1-\2-\3" "2024/02/14"

# 去除多余空格
python3 script/main.py sub "\s+" " " "你好     世界"
```

### 场景 4: 查看正则分组

```bash
# 解析命令行参数
python3 script/main.py groups "--(\w+)=([^\s]+)" "--name=test --port=8080"

# 解析CSV格式
python3 script/main.py groups "([^,]+),([^,]+),([^,]+)" "张三,25,北京"
```

## 正则表达式语法速查

| 符号 | 说明 |
|------|------|
| `.` | 匹配任意字符（除换行） |
| `\d` | 匹配数字 |
| `\w` | 匹配字母数字下划线 |
| `\s` | 匹配空白字符 |
| `^` | 匹配行首 |
| `$` | 匹配行尾 |
| `*` | 匹配0次或多次 |
| `+` | 匹配1次或多次 |
| `?` | 匹配0次或1次 |
| `{n}` | 匹配n次 |
| `{n,}` | 匹配至少n次 |
| `{n,m}` | 匹配n到m次 |
| `[abc]` | 匹配a、b或c |
| `[^abc]` | 匹配非a、b、c的字符 |
| `()` | 捕获分组 |
| `(?:)` | 非捕获分组 |
| `|` | 或操作 |

## 注意事项

1. 特殊字符需要转义：`. ^ $ * + ? { } [ ] \ | ( )`
2. 使用 `.*` 时注意贪婪匹配，可用 `.*?` 进行非贪婪匹配
3. 捕获分组编号从1开始，`group(0)` 是整个匹配结果
4. Python默认使用Unicode模式，可匹配中文等Unicode字符

## 目录结构

```
regex-assistant/
├── SKILL.md              # 技能说明文档(本文件)
├── script/
│   └── main.py          # 主程序
└── tests/               # 测试用例
```
