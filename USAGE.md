# Qt Translation MCP 使用指南

## 安装步骤

### 1. 安装依赖

在项目目录下运行：

```bash
pip install -e .
```

这会安装所需的依赖：
- mcp (Model Context Protocol)
- gitpython (Git 操作)
- lxml (XML 解析)

### 2. 配置 Kiro MCP

在 Kiro 中配置这个 MCP 服务器：

**方式 A：工作区配置**（推荐）

创建或编辑 `.kiro/settings/mcp.json`：

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

**方式 B：全局配置**

编辑 `~/.kiro/settings/mcp.json`（同样的格式）

### 3. 重启或重连 MCP

- 在 Kiro 中打开 MCP Server 视图
- 找到 "qt-translation" 服务器
- 点击重连按钮

## 使用流程

### 场景 1：从 Git 提交历史收集新增文案并翻译

#### 步骤 1：导出待翻译内容

在 Kiro 中与 AI 对话：

```
使用 qt-translation MCP 的 export_for_translation 工具，参数：
- source: "git"
- repo_path: "/path/to/your/qt/project"
- commit_range: "HEAD~10..HEAD"
- multi_language: true
```

或者直接说：

```
帮我从 /path/to/your/qt/project 的最近 10 个提交中提取需要翻译的文案，
导出为多语言表格
```

#### 步骤 2：翻译表格

MCP 会返回类似这样的表格：

```markdown
| 序号 | Context | 英文原文 | 简体中文(zh_CN) | 香港繁体(zh_HK) | 台湾繁体(zh_TW) | 维吾尔语(ug) | 藏语(bo) | 备注 |
|------|---------|----------|----------------|----------------|----------------|------------|--------|------|
| 1 | MainWindow | Open File | | | | | | |
| 2 | MainWindow | Save File | | | | | | |
```

然后对 AI 说：

```
请翻译这个表格，填充五种语言翻译。注意：
- 简体中文：中国大陆用词
- 香港繁体：香港用词习惯
- 台湾繁体：台湾用词习惯
- 维吾尔语：维吾尔文翻译
- 藏语：藏文翻译
```

#### 步骤 3：导入翻译

AI 翻译完成后，对它说：

```
使用 import_translations 工具导入翻译，参数：
- ts_base_path: "/path/to/your/translations/app"
- translation_data: [AI 会自动填充翻译后的表格]
- multi_language: true
```

或者简单说：

```
把这些翻译导入到 /path/to/your/translations/app 的 TS 文件中
```

完成！三个 TS 文件会被自动更新。

### 场景 2：翻译现有 TS 文件中的未翻译条目

#### 步骤 1：导出未翻译条目

```
使用 export_for_translation 工具，从 /path/to/app_zh_CN.ts 导出未翻译的条目
```

#### 步骤 2-3：同上

### 场景 3：查看翻译状态

```
使用 parse_ts_file 工具解析 /path/to/app_zh_CN.ts
```

会显示：
- 总条目数
- 已翻译数量
- 未翻译数量

### 场景 4：查找所有未翻译条目

```
使用 find_untranslated 工具查找 /path/to/app_zh_CN.ts 中的未翻译条目
```

## 完整示例对话

```
你：帮我处理 Qt 项目的翻译

AI：好的，请提供你的 Qt 项目路径和翻译文件位置

你：项目在 /home/user/myapp，翻译文件在 /home/user/myapp/translations/myapp

AI：我来从最近的提交中收集需要翻译的文案
[调用 export_for_translation]
[返回表格]

AI：我已经导出了 15 个待翻译条目，现在我来翻译它们...
[AI 翻译表格]

AI：翻译完成，现在导入到 TS 文件
[调用 import_translations]

AI：完成！已更新：
- myapp_zh_CN.ts: 15 个条目
- myapp_zh_HK.ts: 15 个条目  
- myapp_zh_TW.ts: 15 个条目
- myapp_ug.ts: 15 个条目
- myapp_bo.ts: 15 个条目
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

## 可用工具列表

1. **export_for_translation** - 导出待翻译表格
2. **import_translations** - 导入翻译结果
3. **parse_ts_file** - 解析 TS 文件状态
4. **find_untranslated** - 查找未翻译条目
5. **collect_translations_from_git** - 从 Git 收集文案（底层工具）
6. **insert_translations** - 插入翻译（底层工具）

通常你只需要使用前 4 个工具。

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
