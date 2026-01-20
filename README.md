# Qt Translation MCP Server

基于 MCP (Model Context Protocol) 的 Qt 多语言翻译工具服务器。

专为简体中文、香港繁体、台湾繁体三种语言优化，通过 LLM 辅助完成高质量翻译。

## 功能特性

✅ 从 Git 提交历史自动收集需要翻译的文案  
✅ 导出 Markdown 表格供 LLM 翻译  
✅ 一次性处理五种语言（简体中文、香港繁体、台湾繁体、维吾尔语、藏语）  
✅ 自动更新对应的 TS 文件（zh_CN.ts、zh_HK.ts、zh_TW.ts、ug.ts、bo.ts）  
✅ 解析和管理现有翻译文件  
✅ 查找未翻译条目  
✅ 最小化文件变更，保持原有格式（优化的 Git diff）

## 快速开始

### 1. 安装

```bash
pip install -e .
```

### 2. 配置 Kiro MCP

**方式 A：工作区配置**（推荐）

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

**方式 B：使用虚拟环境**

如果使用虚拟环境，配置如下：

```json
{
  "mcpServers": {
    "qt-translation": {
      "command": "/path/to/venv/bin/python3",
      "args": ["-m", "qt_translation_mcp"],
      "disabled": false
    }
  }
}
```

**方式 C：全局配置**

编辑 `~/.kiro/settings/mcp.json`（使用相同格式）

### 3. 重启或重连 MCP

- 在 Kiro 中打开 MCP Server 视图
- 找到 "qt-translation" 服务器
- 点击重连按钮

### 4. 使用

在 Kiro 中与 AI 对话：

```
帮我从 /path/to/qt/project 的最近 10 个提交中提取需要翻译的文案，
并翻译成简体中文、香港繁体、台湾繁体、维吾尔语、藏语
```

AI 会自动：
1. 调用 MCP 导出待翻译表格
2. 翻译成五种语言
3. 导入到对应的 TS 文件

## 工作流程

```
Git 提交 → 提取文案 → 导出表格 → LLM 翻译 → 导入 TS 文件
```

## 使用场景

### 场景 1：从 Git 提交历史收集新增文案并翻译

```
使用 export_for_translation 工具，参数：
- source: "git"
- repo_path: "/path/to/your/qt/project"
- commit_range: "HEAD~10..HEAD"
- multi_language: true
```

或直接说：
```
帮我从 /path/to/your/qt/project 的最近 10 个提交中提取需要翻译的文案，
导出为多语言表格
```

### 场景 2：翻译现有 TS 文件中的未翻译条目

```
使用 export_for_translation 工具，从 /path/to/app_zh_CN.ts 导出未翻译的条目
```

### 场景 3：查看翻译状态

```
使用 parse_ts_file 工具解析 /path/to/app_zh_CN.ts
```

### 场景 4：查找所有未翻译条目

```
使用 find_untranslated 工具查找 /path/to/app_zh_CN.ts 中的未翻译条目
```

## 可用工具

1. **export_for_translation** - 导出待翻译表格（支持从 Git 或 TS 文件）
2. **import_translations** - 导入翻译结果到 TS 文件
3. **parse_ts_file** - 解析 TS 文件状态
4. **find_untranslated** - 查找未翻译条目
5. **collect_translations_from_git** - 从 Git 收集文案（底层工具）
6. **insert_translations** - 插入翻译（底层工具）

通常你只需要使用前 4 个工具。

## 文档

- [详细使用指南](USAGE.md) - 完整的安装和使用说明
- [翻译工作流程](examples/translation_workflow.md) - LLM 多语言翻译流程
- [示例用法](examples/example_usage.md) - 各种使用场景示例
- [多语言说明](LANGUAGE_NOTES.md) - 各语言特点和注意事项
- [更新日志](CHANGELOG.md) - 最新优化和改进
- [潜在问题](POTENTIAL_ISSUES.md) - 性能和稳定性注意事项

## 支持的语言

| 语言代码 | 语言名称 | TS 文件后缀 |
|---------|---------|------------|
| zh_CN | 简体中文 | _zh_CN.ts |
| zh_HK | 香港繁体 | _zh_HK.ts |
| zh_TW | 台湾繁体 | _zh_TW.ts |
| ug | 维吾尔语 | _ug.ts |
| bo | 藏语 | _bo.ts |

## 示例

**导出待翻译内容：**
```
从 Git 历史收集 → 生成多语言表格
```

**LLM 翻译表格：**
```markdown
| 序号 | Context | 英文原文 | 简体中文(zh_CN) | 香港繁体(zh_HK) | 台湾繁体(zh_TW) | 维吾尔语(ug) | 藏语(bo) | 备注 |
|------|---------|----------|----------------|----------------|----------------|------------|--------|------|
| 1 | MainWindow | Open File | 打开文件 | 開啟檔案 | 開啟檔案 | ھۆججەت ئېچىش | ཡིག་ཆ་ཁ་ཕྱེ། | File menu action |
| 2 | MainWindow | Software | 软件 | 軟件 | 軟體 | يۇمشاق دېتال | མཉེན་ཆས། | |
```

**自动导入：**
```
app_zh_CN.ts ← 简体中文
app_zh_HK.ts ← 香港繁体
app_zh_TW.ts ← 台湾繁体
app_ug.ts ← 维吾尔语
app_bo.ts ← 藏语
```

## 文件路径说明

假设你的项目结构：

```
/home/user/myapp/
├── src/
│   ├── main.cpp
│   └── mainwindow.cpp
└── translations/
    ├── myapp_zh_CN.ts  (简体中文)
    ├── myapp_zh_HK.ts  (香港繁体)
    ├── myapp_zh_TW.ts  (台湾繁体)
    ├── myapp_ug.ts     (维吾尔语)
    └── myapp_bo.ts     (藏语)
```

使用时：
- `repo_path`: `/home/user/myapp`
- `ts_base_path`: `/home/user/myapp/translations/myapp`（不含 _zh_CN.ts 后缀）

## 最新优化

### 最小化文件变更

优化了 TS 文件更新机制：
- ✅ 只修改新增或修改的翻译条目
- ✅ 保持原有文件格式和结构
- ✅ Git diff 清晰显示真正的变更
- ✅ 更好的版本控制体验

详见 [CHANGELOG.md](CHANGELOG.md)

## 故障排查

### MCP 服务器无法启动

1. 检查 Python 环境：`python --version`（需要 >= 3.10）
2. 检查依赖安装：`pip list | grep mcp`
3. 查看 Kiro 的 MCP 日志

### 找不到 Git 仓库

确保 `repo_path` 指向包含 `.git` 目录的项目根目录

### TS 文件无法更新

1. 检查文件路径是否正确
2. 确保有写入权限
3. 检查 TS 文件是否是有效的 XML 格式

### 翻译没有被识别

确保 LLM 返回的表格格式正确，特别是：
- 表格分隔符 `|` 要对齐
- 不要删除或修改表头
- 翻译内容填在正确的列中

## 提示

1. **批量处理**：一次可以处理多个提交范围的文案
2. **增量更新**：MCP 会自动跳过已存在的翻译条目
3. **备份**：首次使用前建议备份 TS 文件
4. **验证**：导入后可以用 Qt Linguist 打开 TS 文件验证
5. **性能**：处理大量翻译时注意 [POTENTIAL_ISSUES.md](POTENTIAL_ISSUES.md) 中的建议

## 依赖

- Python >= 3.10
- mcp >= 0.9.0
- gitpython >= 3.1.0
- lxml >= 4.9.0

## License

MIT
