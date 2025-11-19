"""Translation table formatter and parser"""

import re
from typing import List, Dict


class TranslationTable:
    """翻译表格的格式化和解析工具"""
    
    # 支持的语言配置
    LANGUAGES = {
        'zh_CN': '简体中文',
        'zh_HK': '香港繁体',
        'zh_TW': '台湾繁体'
    }
    
    @staticmethod
    def create_table(entries: List[Dict], target_language: str = "中文") -> str:
        """创建 Markdown 格式的翻译表格（单语言版本）
        
        Args:
            entries: 翻译条目列表
            target_language: 目标语言名称
        
        Returns:
            Markdown 格式的表格字符串
        """
        if not entries:
            return "没有待翻译的条目"
        
        # 表头
        table = f"| 序号 | Context | 英文原文 | {target_language}翻译 | 备注 |\n"
        table += "|------|---------|----------|----------|------|\n"
        
        # 表格内容
        for idx, entry in enumerate(entries, 1):
            context = entry.get('context', '')
            source = entry.get('source', '')
            comment = entry.get('comment', '')
            
            # 转义表格中的特殊字符
            context = TranslationTable._escape_markdown(context)
            source = TranslationTable._escape_markdown(source)
            comment = TranslationTable._escape_markdown(comment)
            
            table += f"| {idx} | {context} | {source} | | {comment} |\n"
        
        return table
    
    @staticmethod
    def create_multi_language_table(entries: List[Dict]) -> str:
        """创建多语言翻译表格（简体、香港繁体、台湾繁体）
        
        Args:
            entries: 翻译条目列表
        
        Returns:
            Markdown 格式的多语言表格字符串
        """
        if not entries:
            return "没有待翻译的条目"
        
        # 表头
        table = "| 序号 | Context | 英文原文 | 简体中文(zh_CN) | 香港繁体(zh_HK) | 台湾繁体(zh_TW) | 备注 |\n"
        table += "|------|---------|----------|----------------|----------------|----------------|------|\n"
        
        # 表格内容
        for idx, entry in enumerate(entries, 1):
            context = entry.get('context', '')
            source = entry.get('source', '')
            comment = entry.get('comment', '')
            
            # 转义表格中的特殊字符
            context = TranslationTable._escape_markdown(context)
            source = TranslationTable._escape_markdown(source)
            comment = TranslationTable._escape_markdown(comment)
            
            table += f"| {idx} | {context} | {source} | | | | {comment} |\n"
        
        return table
    
    @staticmethod
    def parse_markdown_table(markdown_table: str) -> List[Dict]:
        """解析 Markdown 表格，提取翻译结果（单语言版本）
        
        Args:
            markdown_table: Markdown 格式的表格字符串
        
        Returns:
            翻译条目列表
        """
        translations = []
        lines = markdown_table.strip().split('\n')
        
        # 跳过表头和分隔线
        data_lines = [line for line in lines if line.strip().startswith('|')]
        if len(data_lines) <= 2:
            return translations
        
        # 解析数据行（跳过表头和分隔线）
        for line in data_lines[2:]:
            parts = [p.strip() for p in line.split('|')]
            # 格式: | 序号 | Context | 英文原文 | 翻译 | 备注 |
            if len(parts) >= 6:
                context = parts[2]
                source = parts[3]
                translation = parts[4]
                comment = parts[5] if len(parts) > 5 else ""
                
                # 只添加有翻译内容的条目
                if translation:
                    translations.append({
                        'context': TranslationTable._unescape_markdown(context),
                        'source': TranslationTable._unescape_markdown(source),
                        'translation': TranslationTable._unescape_markdown(translation),
                        'comment': TranslationTable._unescape_markdown(comment)
                    })
        
        return translations
    
    @staticmethod
    def parse_multi_language_table(markdown_table: str) -> Dict[str, List[Dict]]:
        """解析多语言 Markdown 表格
        
        Args:
            markdown_table: Markdown 格式的多语言表格字符串
        
        Returns:
            字典，键为语言代码(zh_CN, zh_HK, zh_TW)，值为翻译条目列表
        """
        result = {
            'zh_CN': [],
            'zh_HK': [],
            'zh_TW': []
        }
        
        lines = markdown_table.strip().split('\n')
        
        # 跳过表头和分隔线
        data_lines = [line for line in lines if line.strip().startswith('|')]
        if len(data_lines) <= 2:
            return result
        
        # 解析数据行（跳过表头和分隔线）
        for line in data_lines[2:]:
            parts = [p.strip() for p in line.split('|')]
            # 格式: | 序号 | Context | 英文原文 | 简体中文 | 香港繁体 | 台湾繁体 | 备注 |
            if len(parts) >= 8:
                context = parts[2]
                source = parts[3]
                zh_cn = parts[4]
                zh_hk = parts[5]
                zh_tw = parts[6]
                comment = parts[7] if len(parts) > 7 else ""
                
                # 为每种语言添加翻译条目
                if zh_cn:
                    result['zh_CN'].append({
                        'context': TranslationTable._unescape_markdown(context),
                        'source': TranslationTable._unescape_markdown(source),
                        'translation': TranslationTable._unescape_markdown(zh_cn),
                        'comment': TranslationTable._unescape_markdown(comment)
                    })
                
                if zh_hk:
                    result['zh_HK'].append({
                        'context': TranslationTable._unescape_markdown(context),
                        'source': TranslationTable._unescape_markdown(source),
                        'translation': TranslationTable._unescape_markdown(zh_hk),
                        'comment': TranslationTable._unescape_markdown(comment)
                    })
                
                if zh_tw:
                    result['zh_TW'].append({
                        'context': TranslationTable._unescape_markdown(context),
                        'source': TranslationTable._unescape_markdown(source),
                        'translation': TranslationTable._unescape_markdown(zh_tw),
                        'comment': TranslationTable._unescape_markdown(comment)
                    })
        
        return result
    
    @staticmethod
    def create_json(entries: List[Dict]) -> str:
        """创建 JSON 格式的翻译数据
        
        Args:
            entries: 翻译条目列表
        
        Returns:
            JSON 字符串
        """
        import json
        
        data = []
        for entry in entries:
            data.append({
                'context': entry.get('context', ''),
                'source': entry.get('source', ''),
                'translation': '',  # 待填充
                'comment': entry.get('comment', '')
            })
        
        return json.dumps(data, ensure_ascii=False, indent=2)
    
    @staticmethod
    def _escape_markdown(text: str) -> str:
        """转义 Markdown 表格中的特殊字符"""
        if not text:
            return ''
        # 替换管道符和换行符
        text = text.replace('|', '\\|')
        text = text.replace('\n', ' ')
        return text
    
    @staticmethod
    def _unescape_markdown(text: str) -> str:
        """反转义 Markdown 表格中的特殊字符"""
        if not text:
            return ''
        text = text.replace('\\|', '|')
        return text
