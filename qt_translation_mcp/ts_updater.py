"""Qt TS file updater"""

from pathlib import Path
from typing import List, Dict, Optional
from lxml import etree
import re


class TSUpdater:
    """Qt TS 翻译文件更新器"""
    
    def insert_translations(self, ts_files: List[str], translations: List[Dict]) -> Dict[str, int]:
        """将翻译条目插入到 TS 文件中
        
        Args:
            ts_files: TS 文件路径列表
            translations: 翻译条目列表，每个条目包含 context, source, translation, comment
        
        Returns:
            每个文件插入/更新的条目数量
        """
        results = {}
        
        for ts_file in ts_files:
            count = self._insert_to_file(ts_file, translations)
            results[ts_file] = count
        
        return results
    
    def _insert_to_file(self, ts_file_path: str, translations: List[Dict]) -> int:
        """将翻译条目插入到单个 TS 文件
        
        Args:
            ts_file_path: TS 文件路径
            translations: 翻译条目列表
        
        Returns:
            插入/更新的条目数量
        """
        ts_path = Path(ts_file_path)
        
        # 如果文件不存在，创建新的 TS 文件
        if not ts_path.exists():
            root = self._create_empty_ts()
            tree = etree.ElementTree(root)
            message_index = {}
            # 新文件需要完整写入
            modified_count = 0
            for trans in translations:
                context_name = trans.get('context', '')
                source_text = trans.get('source', '')
                translation_text = trans.get('translation', '')
                comment_text = trans.get('comment', '')
                
                if not context_name or not source_text:
                    continue
                
                context_elem = self._find_or_create_context(root, context_name)
                self._create_message(context_elem, source_text, translation_text, comment_text)
                modified_count += 1
            
            if modified_count > 0:
                self._safe_write(tree, ts_path)
            return modified_count
        
        # 对于现有文件，使用精确的文本替换方式
        return self._update_file_by_text_replacement(ts_path, translations)
    
    def _create_empty_ts(self) -> etree.Element:
        """创建空的 TS 文件结构"""
        root = etree.Element('TS')
        root.set('version', '2.1')
        return root
    
    def _find_or_create_context(self, root: etree.Element, context_name: str) -> etree.Element:
        """查找或创建 context 元素"""
        # 查找现有 context
        for context_elem in root.findall('context'):
            name_elem = context_elem.find('name')
            if name_elem is not None and name_elem.text == context_name:
                return context_elem
        
        # 创建新 context
        context_elem = etree.SubElement(root, 'context')
        name_elem = etree.SubElement(context_elem, 'name')
        name_elem.text = context_name
        
        return context_elem
    
    def _find_message(self, context_elem: etree.Element, source_text: str) -> etree.Element:
        """查找指定的 message 元素"""
        for message_elem in context_elem.findall('message'):
            source_elem = message_elem.find('source')
            if source_elem is not None and source_elem.text == source_text:
                return message_elem
        return None
    
    def _update_message(self, message_elem: etree.Element, translation_text: str, comment_text: str) -> bool:
        """更新现有 message 元素，仅当内容有变化时
        
        Returns:
            是否进行了修改
        """
        modified = False
        
        # 更新 translation
        translation_elem = message_elem.find('translation')
        if translation_elem is None:
            translation_elem = etree.SubElement(message_elem, 'translation')
        
        # 检查翻译内容是否需要更新
        current_translation = translation_elem.text or ""
        if translation_text and current_translation != translation_text:
            translation_elem.text = translation_text
            # 移除 unfinished 标记
            if 'type' in translation_elem.attrib:
                del translation_elem.attrib['type']
            modified = True
        
        # 更新 comment（如果提供）
        if comment_text:
            comment_elem = message_elem.find('comment')
            current_comment = comment_elem.text if comment_elem is not None else ""
            if current_comment != comment_text:
                if comment_elem is None:
                    comment_elem = etree.SubElement(message_elem, 'comment')
                comment_elem.text = comment_text
                modified = True
        
        return modified
    
    def _create_message(self, context_elem: etree.Element, source_text: str, 
                       translation_text: str, comment_text: str):
        """创建新的 message 元素"""
        message_elem = etree.SubElement(context_elem, 'message')
        
        # 添加 source
        source_elem = etree.SubElement(message_elem, 'source')
        source_elem.text = source_text
        
        # 添加 translation
        translation_elem = etree.SubElement(message_elem, 'translation')
        if translation_text:
            translation_elem.text = translation_text
        else:
            translation_elem.set('type', 'unfinished')
        
        # 添加 comment（如果有）
        if comment_text:
            comment_elem = etree.SubElement(message_elem, 'comment')
            comment_elem.text = comment_text
    
    def _build_message_index(self, root: etree.Element) -> Dict[str, Dict[str, etree.Element]]:
        """构建 message 索引以加速查找
        
        Returns:
            嵌套字典: {context_name: {source_text: message_element}}
        """
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
                if source_elem is not None and source_elem.text:
                    index[context_name][source_elem.text] = message_elem
        
        return index
    
    def _update_file_by_text_replacement(self, ts_path: Path, translations: List[Dict]) -> int:
        """通过文本替换方式更新文件，只修改翻译相关的内容
        
        Args:
            ts_path: TS 文件路径
            translations: 翻译条目列表
        
        Returns:
            修改的条目数量
        """
        # 读取原始文件内容
        with open(ts_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        modified_count = 0
        
        for trans in translations:
            context_name = trans.get('context', '')
            source_text = trans.get('source', '')
            translation_text = trans.get('translation', '')
            
            if not context_name or not source_text or not translation_text:
                continue
            
            # 转义特殊字符用于正则表达式
            escaped_context = re.escape(context_name)
            escaped_source = re.escape(source_text)
            
            # 查找对应的 message 块，匹配 context 和 source
            # 这个正则表达式会匹配包含指定 context 和 source 的 message 块
            pattern = (
                r'(<context>\s*<name>' + escaped_context + r'</name>.*?'
                r'<message[^>]*>.*?'
                r'<source>' + escaped_source + r'</source>\s*'
                r'<translation[^>]*>)(.*?)(</translation>)'
            )
            
            def replace_translation(match):
                nonlocal modified_count
                prefix = match.group(1)
                current_trans = match.group(2)
                suffix = match.group(3)
                
                # 只有当翻译内容不同时才替换
                if current_trans.strip() != translation_text.strip():
                    modified_count += 1
                    # 移除 type="unfinished" 属性
                    prefix = re.sub(r'\s+type="unfinished"', '', prefix)
                    return prefix + translation_text + suffix
                return match.group(0)
            
            # 使用 DOTALL 标志让 . 匹配换行符
            content = re.sub(pattern, replace_translation, content, flags=re.DOTALL)
        
        # 只有在内容确实改变时才写入文件
        if content != original_content and modified_count > 0:
            self._safe_write_text(content, ts_path)
        
        return modified_count
    
    def _safe_write_text(self, content: str, target_path: Path):
        """安全写入文本内容，使用临时文件保护原文件
        
        Args:
            content: 文件内容
            target_path: 目标文件路径
        """
        import tempfile
        import shutil
        import os
        
        # 创建临时文件
        temp_fd, temp_path = tempfile.mkstemp(suffix='.ts', dir=target_path.parent)
        
        try:
            # 写入临时文件
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 成功后替换原文件
            shutil.move(temp_path, str(target_path))
        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            raise e
    
    def _safe_write(self, tree: etree.ElementTree, target_path: Path):
        """安全写入文件，使用临时文件保护原文件
        
        Args:
            tree: XML 树
            target_path: 目标文件路径
        """
        import tempfile
        import shutil
        import os
        
        # 创建临时文件
        temp_fd, temp_path = tempfile.mkstemp(suffix='.ts', dir=target_path.parent)
        
        try:
            # 关闭文件描述符
            os.close(temp_fd)
            
            # 写入临时文件
            tree.write(
                temp_path,
                encoding='utf-8',
                xml_declaration=True,
                pretty_print=True,
                doctype='<!DOCTYPE TS>'
            )
            
            # 成功后替换原文件
            shutil.move(temp_path, str(target_path))
        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            raise e
    
    def update_translation(self, ts_file_path: str, context: str, source: str, translation: str) -> bool:
        """更新现有翻译条目
        
        Args:
            ts_file_path: TS 文件路径
            context: 上下文名称
            source: 源文本
            translation: 翻译文本
        
        Returns:
            是否成功更新
        """
        ts_path = Path(ts_file_path)
        if not ts_path.exists():
            return False
        
        # 使用文本替换方式更新
        translations = [{
            'context': context,
            'source': source,
            'translation': translation
        }]
        
        modified_count = self._update_file_by_text_replacement(ts_path, translations)
        return modified_count > 0
