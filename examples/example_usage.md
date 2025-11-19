# 使用示例

## 1. 从 Git 历史收集翻译文案

```
使用工具: collect_translations_from_git

参数:
- repo_path: "/path/to/your/qt/project"
- commit_range: "HEAD~20..HEAD"
- file_patterns: ["*.cpp", "*.h", "*.ui"]
```

这将扫描最近 20 个提交中的 C++ 和头文件，提取所有 tr() 和 translate() 函数调用。

## 2. 解析现有 TS 文件

```
使用工具: parse_ts_file

参数:
- ts_file_path: "/path/to/translations/app_zh_CN.ts"
```

查看当前翻译文件的状态，包括已翻译和未翻译的条目数量。

## 3. 插入新翻译

```
使用工具: insert_translations

参数:
- ts_files: [
    "/path/to/translations/app_zh_CN.ts",
    "/path/to/translations/app_en_US.ts"
  ]
- translations: [
    {
      "context": "MainWindow",
      "source": "Open File",
      "translation": "打开文件",
      "comment": "File menu action"
    },
    {
      "context": "MainWindow",
      "source": "Save File",
      "translation": "保存文件"
    }
  ]
```

将新的翻译条目批量插入到多个语言的 TS 文件中。

## 4. 查找未翻译条目

```
使用工具: find_untranslated

参数:
- ts_file_path: "/path/to/translations/app_zh_CN.ts"
```

列出所有需要翻译的条目，方便进行翻译工作。

## 完整工作流程

1. 从 Git 提交历史收集新增的翻译文案
2. 解析现有的 TS 文件，了解当前状态
3. 将收集到的新文案插入到各语言的 TS 文件中（初始为未翻译状态）
4. 使用 Qt Linguist 或其他工具完成实际翻译
5. 定期检查未翻译条目，确保翻译完整性
