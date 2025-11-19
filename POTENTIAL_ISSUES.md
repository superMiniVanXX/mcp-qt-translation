# MCP 处理过程中可能导致卡死的问题分析

## 🔴 高风险问题

### 1. Git 仓库操作可能卡死
**位置**: `git_collector.py` - `collect_translations()`

**问题**:
```python
commits = list(self.repo.iter_commits(commit_range))
```

**风险**:
- 如果 commit_range 范围过大（如 `HEAD~1000..HEAD`），会加载大量提交
- 没有超时机制
- 没有进度反馈
- 可能导致内存溢出

**建议修复**:
```python
# 添加最大提交数限制
MAX_COMMITS = 100

commits = list(self.repo.iter_commits(commit_range, max_count=MAX_COMMITS))
```

### 2. 大文件解析可能卡死
**位置**: `ts_parser.py` - `parse()`

**问题**:
```python
self.tree = etree.parse(str(self.ts_file_path))
```

**风险**:
- 如果 TS 文件非常大（数万条翻译），解析会很慢
- 没有文件大小检查
- 没有超时机制
- 内存占用可能很大

**建议修复**:
```python
# 添加文件大小检查
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

file_size = self.ts_file_path.stat().st_size
if file_size > MAX_FILE_SIZE:
    raise ValueError(f"TS 文件过大: {file_size / 1024 / 1024:.2f}MB")
```

### 3. 嵌套循环性能问题
**位置**: `ts_updater.py` - `_insert_to_file()`

**问题**:
```python
for trans in translations:  # O(n)
    context_elem = self._find_or_create_context(root, context_name)
    existing_message = self._find_message(context_elem, source_text)  # O(m)
```

**风险**:
- 时间复杂度 O(n*m)，n 是翻译条目数，m 是每个 context 的 message 数
- 如果有 1000 条翻译，每个 context 有 1000 条 message，需要 100 万次查找
- 没有使用索引或缓存

**建议修复**:
```python
# 预先构建索引
def _build_message_index(self, root):
    """构建 message 索引以加速查找"""
    index = {}
    for context_elem in root.findall('context'):
        name_elem = context_elem.find('name')
        if name_elem is None:
            continue
        context_name = name_elem.text
        
        if context_name not in index:
            index[context_name] = {}
        
        for message_elem in context_elem.findall('message'):
            source_elem = message_elem.find('source')
            if source_elem is not None:
                index[context_name][source_elem.text] = message_elem
    
    return index
```

## 🟡 中风险问题

### 4. 正则表达式回溯
**位置**: `git_collector.py` - `TR_PATTERNS`

**问题**:
```python
r'tr\s*\(\s*["\']([^"\']+)["\']\s*\)'
```

**风险**:
- 如果代码行很长且包含复杂字符串，正则可能回溯很多次
- 没有超时保护

**建议**: 使用更严格的正则或限制匹配长度

### 5. 文件写入没有错误恢复
**位置**: `ts_updater.py` - `_insert_to_file()`

**问题**:
```python
tree.write(str(ts_path), encoding='utf-8', xml_declaration=True, pretty_print=False)
```

**风险**:
- 如果写入失败（磁盘满、权限问题），原文件可能损坏
- 没有备份机制

**建议修复**:
```python
# 先写入临时文件，成功后再替换
import tempfile
import shutil

temp_fd, temp_path = tempfile.mkstemp(suffix='.ts')
try:
    tree.write(temp_path, encoding='utf-8', xml_declaration=True, pretty_print=False)
    shutil.move(temp_path, str(ts_path))
finally:
    if os.path.exists(temp_path):
        os.unlink(temp_path)
```

### 6. 表格解析没有行数限制
**位置**: `translation_table.py` - `parse_multi_language_table()`

**问题**:
```python
for line in data_lines[2:]:  # 处理所有行
```

**风险**:
- 如果 LLM 返回超大表格（数千行），处理会很慢
- 没有行数限制

**建议**: 添加最大行数检查

## 🟢 低风险但需要注意

### 7. 异常处理不完整
**位置**: `server.py` - `call_tool()`

**问题**:
```python
except Exception as e:
    logger.error(f"Tool execution error: {e}", exc_info=True)
    return [TextContent(type="text", text=f"错误: {str(e)}")]
```

**风险**:
- 捕获所有异常可能隐藏严重问题
- 没有区分可恢复和不可恢复的错误

### 8. 没有进度反馈
**问题**: 所有长时间操作都没有进度反馈

**影响**: 用户不知道是卡死还是正在处理

## 建议的优化优先级

1. **立即修复**: 添加 Git 提交数限制（问题 1）
2. **立即修复**: 添加文件大小检查（问题 2）
3. **高优先级**: 优化嵌套循环，使用索引（问题 3）
4. **中优先级**: 添加文件写入保护（问题 5）
5. **低优先级**: 改进异常处理和进度反馈
