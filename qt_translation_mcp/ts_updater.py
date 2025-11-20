"""Qt TS file updater"""

from pathlib import Path
from typing import List, Dict, Optional, Callable, Tuple
from lxml import etree
import re
from .logger import get_logger

logger = get_logger('ts_updater')


class TSUpdater:
    """Qt TS 翻译文件更新器"""
    
    def __init__(self):
        """初始化 TS 更新器"""
        self.last_failed_matches = []  # 记录最近一次操作的失败匹配
    
    def insert_translations(self, ts_files: List[str], translations: List[Dict]) -> Dict[str, int]:
        """将翻译条目插入到 TS 文件中
        
        Args:
            ts_files: TS 文件路径列表
            translations: 翻译条目列表，每个条目包含 context, source, translation, comment
        
        Returns:
            每个文件插入/更新的条目数量
        """
        logger.info(f"开始插入翻译，文件数: {len(ts_files)}, 翻译条目数: {len(translations)}")
        results = {}
        
        for ts_file in ts_files:
            logger.info(f"处理文件: {ts_file}")
            count = self._insert_to_file(ts_file, translations)
            results[ts_file] = count
            logger.info(f"文件 {ts_file} 完成，插入/更新 {count} 条")
        
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
    
    def _insert_messages_to_content(self, content: str, translations: List[Dict]) -> Tuple[str, int, List[Dict]]:
        """将新的 message 条目插入到文件内容中（仅当 context 存在时）
        
        Args:
            content: 原始文件内容
            translations: 要插入的翻译条目列表
        
        Returns:
            (修改后的内容, 插入的条目数量, 失败的条目列表)
        """
        inserted_count = 0
        failed_items = []
        
        # 按 context 分组
        by_context = {}
        for trans in translations:
            context_name = trans.get('context', '')
            if context_name not in by_context:
                by_context[context_name] = []
            by_context[context_name].append(trans)
        
        # 对每个 context 进行处理
        for context_name, trans_list in by_context.items():
            # 查找 context 块
            escaped_context = re.escape(context_name)
            context_pattern = (
                r'(<context>\s*<name>' + escaped_context + r'</name>.*?)'
                r'(</context>)'
            )
            
            match = re.search(context_pattern, content, re.DOTALL)
            
            if match:
                # Context 存在，在其末尾插入新的 message
                prefix = match.group(1)
                suffix = match.group(2)
                
                # 构建要插入的 message 元素
                messages_xml = []
                for trans in trans_list:
                    source_text = trans.get('source', '')
                    translation_text = trans.get('translation', '')
                    comment_text = trans.get('comment', '')
                    
                    msg_xml = '    <message>\n'
                    msg_xml += f'        <source>{self._escape_xml(source_text)}</source>\n'
                    if comment_text:
                        msg_xml += f'        <comment>{self._escape_xml(comment_text)}</comment>\n'
                    msg_xml += f'        <translation>{self._escape_xml(translation_text)}</translation>\n'
                    msg_xml += '    </message>\n'
                    
                    messages_xml.append(msg_xml)
                    inserted_count += 1
                    logger.debug(f"  插入到 context '{context_name}': {source_text[:30]}...")
                
                # 替换 context 块
                new_context = prefix + ''.join(messages_xml) + suffix
                content = content[:match.start()] + new_context + content[match.end():]
            else:
                # Context 不存在，记录为失败
                logger.warning(f"  Context '{context_name}' 不存在，无法插入")
                for trans in trans_list:
                    failed_items.append({
                        'context': context_name,
                        'source': trans.get('source', ''),
                        'translation': trans.get('translation', ''),
                        'reason': f"Context '{context_name}' 不存在于 TS 文件中"
                    })
        
        return content, inserted_count, failed_items
    
    def _escape_xml(self, text: str) -> str:
        """转义 XML 特殊字符
        
        Args:
            text: 原始文本
        
        Returns:
            转义后的文本
        """
        if not text:
            return text
        
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&apos;')
        
        return text
    

    
    def _update_file_by_text_replacement(self, ts_path: Path, translations: List[Dict]) -> int:
        """通过文本替换方式更新文件，只修改翻译相关的内容
        
        Args:
            ts_path: TS 文件路径
            translations: 翻译条目列表
        
        Returns:
            修改的条目数量
        """
        logger.debug(f"使用文本替换方式更新文件: {ts_path}")
        
        # 读取原始文件内容
        with open(ts_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.debug(f"文件大小: {len(content)} 字符")
        original_content = content
        modified_count = 0
        skipped_count = 0
        inserted_count = 0
        to_insert = []  # 需要插入的条目
        
        for idx, trans in enumerate(translations, 1):
            context_name = trans.get('context', '')
            source_text = trans.get('source', '')
            translation_text = trans.get('translation', '')
            comment_text = trans.get('comment', '')
            
            if not context_name or not source_text or not translation_text:
                skipped_count += 1
                logger.debug(f"条目 {idx} 跳过: context={bool(context_name)}, source={bool(source_text)}, translation={bool(translation_text)}")
                continue
            
            logger.debug(f"条目 {idx}: [{context_name}] {source_text[:30]}... -> {translation_text[:30]}...")
            
            # 转义特殊字符用于正则表达式
            escaped_source = re.escape(source_text)
            escaped_context = re.escape(context_name)
            
            # 只使用完全匹配策略
            # context 名称必须与 TS 文件中的 <name> 完全一致
            context_pattern = escaped_context.replace(r'\ ', r'\s*') + r'(?=</name>)'
            
            # 查找对应的 message 块，匹配 context 和 source
            pattern = (
                r'(<context>\s*<name>' + context_pattern + r'</name>.*?'
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
                    logger.debug(f"  替换翻译: '{current_trans.strip()[:30]}...' -> '{translation_text[:30]}...'")
                    return prefix + translation_text + suffix
                else:
                    logger.debug(f"  翻译内容相同，跳过")
                return match.group(0)
            
            # 使用 DOTALL 标志让 . 匹配换行符
            before_count = modified_count
            content = re.sub(pattern, replace_translation, content, flags=re.DOTALL)
            
            # 如果匹配失败，说明需要插入新条目
            if modified_count == before_count:
                logger.info(f"  未找到匹配的 message，将作为新条目插入")
                to_insert.append(trans)
        
        # 处理需要插入的条目
        failed_items = []
        if to_insert:
            logger.info(f"开始插入 {len(to_insert)} 个新条目")
            content, inserted, failed_items = self._insert_messages_to_content(content, to_insert)
            inserted_count = inserted
        
        logger.info(f"文本替换完成: 更新 {modified_count} 条，插入 {inserted_count} 条，跳过 {skipped_count} 条，失败 {len(failed_items)} 条")
        
        # 保存失败记录
        self.last_failed_matches = failed_items
        
        # 如果有失败的条目，记录警告
        if failed_items:
            for item in failed_items:
                logger.warning(f"  失败: [{item['context']}] {item['source'][:50]}... - {item['reason']}")
        
        # 只有在内容确实改变时才写入文件
        if content != original_content:
            logger.info(f"写入文件: {ts_path}")
            self._safe_write_text(content, ts_path)
        else:
            logger.info(f"文件无变化，不写入")
        
        return modified_count + inserted_count
    
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
