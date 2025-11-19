"""Git history collector for translation strings"""

import re
from pathlib import Path
from typing import List, Dict
import git


class GitCollector:
    """收集 Git 提交历史中的翻译文案"""
    
    # Qt 翻译函数的正则模式
    TR_PATTERNS = [
        r'tr\s*\(\s*["\']([^"\']+)["\']\s*\)',  # tr("text")
        r'QObject::tr\s*\(\s*["\']([^"\']+)["\']\s*\)',  # QObject::tr("text")
        r'QCoreApplication::translate\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*\)',  # translate("context", "text")
    ]
    
    def __init__(self, repo_path: str):
        """初始化 Git 收集器
        
        Args:
            repo_path: Git 仓库路径
        """
        self.repo_path = Path(repo_path)
        self.repo = git.Repo(repo_path)
    
    def collect_translations(self, commit_range: str, file_patterns: List[str]) -> List[Dict]:
        """从 Git 提交历史中收集翻译文案
        
        Args:
            commit_range: 提交范围，例如 'HEAD~10..HEAD'
            file_patterns: 文件模式列表，例如 ['*.cpp', '*.h']
        
        Returns:
            翻译条目列表
        """
        translations = []
        seen = set()
        
        # 解析提交范围，限制最大提交数防止卡死
        MAX_COMMITS = 200
        commits = list(self.repo.iter_commits(commit_range, max_count=MAX_COMMITS))
        
        for commit in commits:
            # 获取提交的差异
            if commit.parents:
                diffs = commit.parents[0].diff(commit, create_patch=True)
            else:
                # 首次提交
                diffs = commit.diff(git.NULL_TREE, create_patch=True)
            
            for diff in diffs:
                # 检查文件是否匹配模式
                if not self._matches_patterns(diff.b_path, file_patterns):
                    continue
                
                # 只处理新增的行
                if diff.diff:
                    patch = diff.diff.decode('utf-8', errors='ignore')
                    added_lines = [line[1:] for line in patch.split('\n') if line.startswith('+') and not line.startswith('+++')]
                    
                    for line in added_lines:
                        # 提取翻译文案
                        entries = self._extract_translations(line, diff.b_path)
                        for entry in entries:
                            key = (entry['context'], entry['source'])
                            if key not in seen:
                                seen.add(key)
                                translations.append(entry)
        
        return translations
    
    def _matches_patterns(self, filepath: str, patterns: List[str]) -> bool:
        """检查文件路径是否匹配模式"""
        if not filepath:
            return False
        path = Path(filepath)
        for pattern in patterns:
            if path.match(pattern):
                return True
        return False
    
    def _extract_translations(self, line: str, filepath: str) -> List[Dict]:
        """从代码行中提取翻译文案"""
        results = []
        
        # 尝试匹配各种 tr 函数模式
        for pattern in self.TR_PATTERNS:
            matches = re.finditer(pattern, line)
            for match in matches:
                if 'translate' in pattern and len(match.groups()) >= 2:
                    # QCoreApplication::translate("context", "text")
                    context = match.group(1)
                    source = match.group(2)
                else:
                    # tr("text") - 使用文件名作为 context
                    context = Path(filepath).stem
                    source = match.group(1)
                
                results.append({
                    'context': context,
                    'source': source,
                    'file': filepath,
                    'line': line.strip()
                })
        
        return results
