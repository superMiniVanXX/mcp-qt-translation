# Qt Translation MCP Server

基于 MCP (Model Context Protocol) 的 Qt 多语言翻译工具服务器。

专为简体中文、香港繁体、台湾繁体三种语言优化，通过 LLM 辅助完成高质量翻译。

## 功能特性

✅ 从 Git 提交历史自动收集需要翻译的文案  
✅ 导出 Markdown 表格供 LLM 翻译  
✅ 一次性处理三种中文变体（简体、香港繁体、台湾繁体）  
✅ 自动更新对应的 TS 文件（zh_CN.ts、zh_HK.ts、zh_TW.ts）  
✅ 解析和管理现有翻译文件  
✅ 查找未翻译条目

## 快速开始

### 1. 安装

```bash
pip install -e .
```

### 2. 配置 Kiro MCP

在 `.kiro/settings/mcp.json` 中添加：

```json
{
  "mcpServers": {
    "qt-translation": {
      "command": "python",
      "args": ["-m", "qt_translation_mcp"],
      "cwd": "/path/to/this/project",
      "disabled": false
    }
  }
}
```
考虑到你可能在使用虚拟环境，你需要先完成venv配置并install这个模块，配置文件可能更像

```json
{
  "mcpServers": {
    "qt-translation": {
      "command": "/path/to/venv/bin/python3",
      "args": [
        "-m",
        "qt_translation_mcp"
      ],
      "disabled": false
    }
  }
}
```json

### 3. 使用

在 Kiro 中与 AI 对话：

```
帮我从 /path/to/qt/project 的最近 10 个提交中提取需要翻译的文案，
并翻译成简体中文、香港繁体、台湾繁体
```

AI 会自动：
1. 调用 MCP 导出待翻译表格
2. 翻译成三种中文
3. 导入到对应的 TS 文件

## 工作流程

```
Git 提交 → 提取文案 → 导出表格 → LLM 翻译 → 导入 TS 文件
```

## 文档

- [详细使用指南](USAGE.md)
- [翻译工作流程](examples/translation_workflow.md)
- [示例用法](examples/example_usage.md)
- [日志系统使用指南](LOGGING.md) ⭐ 新增

## 支持的语言

| 语言代码 | 语言名称 | TS 文件后缀 |
|---------|---------|------------|
| zh_CN | 简体中文 | _zh_CN.ts |
| zh_HK | 香港繁体 | _zh_HK.ts |
| zh_TW | 台湾繁体 | _zh_TW.ts |

## 示例

**导出待翻译内容：**
```
从 Git 历史收集 → 生成多语言表格
```

**LLM 翻译表格：**
```markdown
| 序号 | Context | 英文原文 | 简体中文 | 香港繁体 | 台湾繁体 | 备注 |
|------|---------|----------|---------|---------|---------|------|
| 1 | MainWindow | Open File | 打开文件 | 開啟檔案 | 開啟檔案 | |
| 2 | MainWindow | Software | 软件 | 軟件 | 軟體 | |
```

**自动导入：**
```
app_zh_CN.ts ← 简体中文
app_zh_HK.ts ← 香港繁体
app_zh_TW.ts ← 台湾繁体
```

## 依赖

- Python >= 3.10
- mcp >= 0.9.0
- gitpython >= 3.1.0
- lxml >= 4.9.0

## License

MIT
