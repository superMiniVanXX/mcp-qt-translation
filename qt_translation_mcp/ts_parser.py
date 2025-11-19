"""Qt TS file parser"""

from pathlib import Path
from typing import List, Dict
from lxml import etree


class TSParser:
    """Qt TS 翻译文件解析器"""
    
    def __init__(self, ts_file_path: str):
        """初始化解析器
        
        Args:
            ts_file_path: TS 文件路径
        """
        self.ts_file_path = Path(ts_file_path)
        self.tree = None
        self.root = None
    
    def parse(self) -> List[Dict]:
        """解析 TS 文件
        
        Returns:
            翻译条目列表
        """
        if not self.ts_file_path.exists():
            raise FileNotFoundError(f"TS 文件不存在: {self.ts_file_path}")
        
        self.tree = etree.parse(str(self.ts_file_path))
        self.root = self.tree.getroot()
        
        entries = []
        
        # 遍历所有 context
        for context_elem in self.root.findall('.//context'):
            context_name = context_elem.find('name')
            if context_name is None:
                continue
            
            context_name = context_name.text
            
            # 遍历该 context 下的所有 message
            for message_elem in context_elem.findall('message'):
                source_elem = message_elem.find('source')
                translation_elem = message_elem.find('translation')
                comment_elem = message_elem.find('comment')
                
                if source_elem is None:
                    continue
                
                source_text = source_elem.text or ""
                translation_text = translation_elem.text if translation_elem is not None else ""
                comment_text = comment_elem.text if comment_elem is not None else ""
                
                # 检查是否已翻译
                is_translated = (
                    translation_elem is not None and
                    translation_elem.get('type') != 'unfinished' and
                    translation_text.strip() != ""
                )
                
                entries.append({
                    'context': context_name,
                    'source': source_text,
                    'translation': translation_text,
                    'comment': comment_text,
                    'translated': is_translated
                })
        
        return entries
    
    def get_contexts(self) -> List[str]:
        """获取所有 context 名称"""
        if self.root is None:
            self.parse()
        
        contexts = []
        for context_elem in self.root.findall('.//context'):
            name_elem = context_elem.find('name')
            if name_elem is not None and name_elem.text:
                contexts.append(name_elem.text)
        
        return contexts
    
    def find_entry(self, context: str, source: str) -> Dict:
        """查找特定的翻译条目
        
        Args:
            context: 上下文名称
            source: 源文本
        
        Returns:
            翻译条目，如果不存在则返回 None
        """
        entries = self.parse()
        for entry in entries:
            if entry['context'] == context and entry['source'] == source:
                return entry
        return None
