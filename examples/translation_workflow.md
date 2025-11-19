# LLM 多语言翻译工作流程

## 完整流程示例（推荐：多语言模式）

### 步骤 1: 导出待翻译内容

**从 Git 历史导出多语言表格：**
```json
{
  "source": "git",
  "repo_path": "/path/to/qt/project",
  "commit_range": "HEAD~5..HEAD",
  "multi_language": true
}
```

**从 TS 文件的未翻译条目导出：**
```json
{
  "source": "ts_file",
  "ts_file_path": "/path/to/app_zh_CN.ts",
  "multi_language": true
}
```

### 步骤 2: MCP 返回多语言表格

MCP 会返回包含三种中文的 Markdown 表格：

```markdown
| 序号 | Context | 英文原文 | 简体中文(zh_CN) | 香港繁体(zh_HK) | 台湾繁体(zh_TW) | 备注 |
|------|---------|----------|----------------|----------------|----------------|------|
| 1 | MainWindow | Open File | | | | File menu action |
| 2 | MainWindow | Save File | | | | |
| 3 | Dialog | Cancel | | | | |
| 4 | Dialog | Confirm | | | | |
```

### 步骤 3: 让 LLM 翻译

将表格发送给 LLM，提示词示例：

```
请翻译以下表格中的英文到三种中文变体，保持表格格式不变：
- 简体中文(zh_CN)：中国大陆使用的简体中文
- 香港繁体(zh_HK)：香港使用的繁体中文
- 台湾繁体(zh_TW)：台湾使用的繁体中文

注意三地用词差异，例如：
- "软件" → 简体：软件，香港：軟件，台湾：軟體
- "网络" → 简体：网络，香港：網絡，台湾：網路

表格：
[粘贴表格]
```

### 步骤 4: LLM 返回翻译后的表格

```markdown
| 序号 | Context | 英文原文 | 简体中文(zh_CN) | 香港繁体(zh_HK) | 台湾繁体(zh_TW) | 备注 |
|------|---------|----------|----------------|----------------|----------------|------|
| 1 | MainWindow | Open File | 打开文件 | 開啟檔案 | 開啟檔案 | File menu action |
| 2 | MainWindow | Save File | 保存文件 | 儲存檔案 | 儲存檔案 | |
| 3 | Dialog | Cancel | 取消 | 取消 | 取消 | |
| 4 | Dialog | Confirm | 确认 | 確認 | 確認 | |
```

### 步骤 5: 导入翻译结果

```json
{
  "ts_base_path": "/path/to/app",
  "translation_data": "[粘贴 LLM 返回的完整表格]",
  "multi_language": true
}
```

MCP 会自动：
- 解析表格中的三种语言
- 更新 `/path/to/app_zh_CN.ts`（简体中文）
- 更新 `/path/to/app_zh_HK.ts`（香港繁体）
- 更新 `/path/to/app_zh_TW.ts`（台湾繁体）

### 步骤 6: 完成

```
多语言翻译导入完成：

- /path/to/app_zh_CN.ts: 4 个条目
- /path/to/app_zh_HK.ts: 4 个条目
- /path/to/app_zh_TW.ts: 4 个条目
```

## 单语言模式（可选）

如果只需要翻译一种语言：

### 导出
```json
{
  "source": "git",
  "repo_path": "/path/to/qt/project",
  "multi_language": false
}
```

### 导入
```json
{
  "ts_base_path": "/path/to/app",
  "translation_data": "[表格]",
  "multi_language": false
}
```

## 常见用词差异参考

| 简体中文 | 香港繁体 | 台湾繁体 | 英文 |
|---------|---------|---------|------|
| 软件 | 軟件 | 軟體 | Software |
| 网络 | 網絡 | 網路 | Network |
| 文件 | 檔案 | 檔案 | File |
| 程序 | 程式 | 程式 | Program |
| 信息 | 資訊 | 資訊 | Information |
| 视频 | 影片 | 影片 | Video |
| 鼠标 | 滑鼠 | 滑鼠 | Mouse |
