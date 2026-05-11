---
name: "fennec-seo-audit"
description: "Runs Fennec SEO Auditor checks for a given URL. Invoke when user wants a quick on-page/technical SEO audit or to verify favicon/meta/schema status."
---

# Fennec SEO 一键审计 Skill（配合 Fennec SEO Auditor 扩展）

本 Skill 用于在桌面端配合 Chrome 扩展 **Fennec SEO Auditor** 使用，对任意页面做一键 SEO 体检，适合：

- 想快速看某个 URL 的 SEO 基础健康度（Title/Meta/H 标签/Canonical 等）
- 检查 favicon、Open Graph、结构化数据是否被正确暴露
- 粗筛技术问题（HTTP 状态码、重定向、索引指示、robots 等）
- 在 GEO 场景下，判断该页面是否具备被大模型优先引用的基础条件

> Chrome 扩展地址：  
> https://chromewebstore.google.com/detail/fennec-seo-auditor/fifppiokpmlgceojhfdjbjjapbephcdo

---

## 使用场景（When to invoke）

在以下情况，可以触发本 Skill：

- 用户给出一个 URL，希望做 **快速 SEO 审计 / 体检**
- 用户想确认 favicon / meta / Open Graph / 结构化数据 是否正确配置
- 写完文章或发布新页面，想检查是否满足基础 SEO / GEO 要求
- 想用真实页面做 GEO 示例：看它在“可索引性 + 语义标注 + 品牌信号”上的表现

不适合的场景：

- 批量爬站、全站技术体检（可作为抽样工具使用，但非爬虫）
- 需要完整日志分析、服务器配置级别诊断

---

## 操作步骤（人类执行部分）

1. 在 Chrome 中安装并启用 Fennec SEO Auditor 扩展  
   地址：`https://chromewebstore.google.com/detail/fennec-seo-auditor/fifppiokpmlgceojhfdjbjjapbephcdo`

2. 打开需要审计的目标页面（例如：某篇博客、某个产品详情页、首页等）

3. 点击浏览器工具栏中的 **Fennec SEO Auditor 图标**：
   - 运行标准审计（On-page / HTML / Links / Images 等）
   - 等待扩展完成分析并展示结果

4. 将审计结果中的关键信息（可以是截图、导出的报告要点或手动摘录）提供给本助手，用于：
   - 解读问题的影响程度
   - 生成待办优化清单（按优先级拆分）
   - 提出符合 Google 搜索 + GEO 的改写 / 调整建议

---

## 本 Skill 的职责（助手应该做什么）

当触发 `fennec-seo` Skill 时，助手应：

1. 引导用户使用 Fennec SEO Auditor 对目标 URL 进行审计（如果尚未执行）
2. 根据用户提供的审计输出，做结构化拆解，包括但不限于：
   - 页面基础信息：Title、Meta Description、H1/H2、URL 结构
   - 技术层面：状态码、Canonical、索引指令、robots、sitemap 相关提示
   - 内容与可读性：字数、关键词覆盖、重复度、大块空白内容等
   - 媒体与链接：图片 ALT、内部链接结构、外链状态
   - 品牌与 GEO 信号：favicon、组织信息、logo 暴露、Schema.org 标注
3. 标记出 **高优先级问题**（会直接影响收录/CTR/可信度的项），给出可执行的改进建议
4. 在 GEO 语境下补充说明：
   - 该页面是否便于被 RAG 系统检索与引用（结构化、语义清晰度）
   - 是否具备清晰的品牌实体信号（Organization / Person / Product 等 Schema）
   - 是否存在可能被模型视为“垃圾页面”或低价值内容的风险

---

## 输出格式建议

在处理 Fennec SEO 审计结果时，建议按以下结构输出（可根据实际情况微调）：

1. **页面概况**
   - URL、Title、H1、主要意图
2. **关键问题一览（含优先级）**
   - 高 / 中 / 低 优先级列表
3. **详细问题与修复建议**
   - 按模块拆分：Meta、内容、内部链接、技术信号、媒体、结构化数据等
4. **GEO / RAG 视角补充**
   - 该页面在“可索引性 + 可引用性 + 品牌实体清晰度”上的评价
   - 进一步建议（比如补充 FAQ Schema、优化段落结构、增强数据与引用）

---

## 注意事项

- 助手不直接调用浏览器或扩展，而是**指导用户使用 Fennec SEO Auditor，并对结果做专业解读**。
- 在给出修改建议时，要兼顾：
  - 传统 SEO：收录、排名、CTR、可读性
  - GEO / RAG：结构清晰、语义明确、有可靠来源、实体信息清楚
- 不要简单复述扩展的结果，要结合用户业务场景，转化为落地可执行的优化动作。
