# 更新日志

## 优化 - 最小化文件变更

### 问题
之前的实现在回填翻译内容到 TS 文件时，会使用 `pretty_print=True` 重新格式化整个 XML 文件，导致：
- 即使只修改了少数翻译条目，整个文件都会被重写
- Git diff 显示大量不必要的变更
- 难以追踪真正的翻译修改

### 解决方案
优化了 `TSUpdater` 类的实现：

1. **保留原有格式**
   - 使用 `XMLParser(remove_blank_text=False, strip_cdata=False)` 解析文件
   - 保存时使用 `pretty_print=False`，保持原有的格式和缩进

2. **智能更新检测**
   - 新增 `_find_message()` 方法：查找现有的翻译条目
   - 新增 `_update_message()` 方法：只在翻译内容真正变化时才更新
   - 分离 `_create_message()` 方法：专门处理新条目的创建

3. **最小化修改**
   - 只修改真正需要更新的翻译条目
   - 如果翻译内容相同，跳过更新
   - 只有在有实际修改时才保存文件

### 影响的文件
- `qt_translation_mcp/ts_updater.py`
  - `_insert_to_file()`: 使用保留格式的解析器，区分新增和更新
  - `_find_message()`: 新方法，查找现有条目
  - `_update_message()`: 新方法，智能更新（仅在内容变化时）
  - `_create_message()`: 新方法，创建新条目
  - `update_translation()`: 使用相同的优化策略

### 使用效果
现在当 LLM 提供翻译内容回填时：
- ✅ 只修改新增或修改的翻译条目
- ✅ 保持原有文件格式和结构
- ✅ Git diff 清晰显示真正的变更
- ✅ 更好的版本控制体验
