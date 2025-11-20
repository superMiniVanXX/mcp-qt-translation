"""Git history collector for translation strings"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
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
        self.context_cache = {}  # 缓存文件的 context 信息
    
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
                    # tr("text") - 需要从文件中提取完整的 context
                    context = self._extract_context_from_file(filepath)
                    source = match.group(1)
                
                results.append({
                    'context': context,
                    'source': source,
                    'file': filepath,
                    'line': line.strip()
                })
        
        return results
    
    def _extract_context_from_file(self, filepath: str) -> str:
        """从 C++ 文件中提取完整的 context（命名空间::类名）
        
        Args:
            filepath: 文件路径
        
        Returns:
            完整的 context 名称，例如 "dccV20::display::BrightnessWidget"
        """
        # 检查缓存
        if filepath in self.context_cache:
            return self.context_cache[filepath]
        
        try:
            # 从 git 读取文件内容
            file_content = self.repo.git.show(f'HEAD:{filepath}')
            
            # 提取类名和命名空间
            namespace, classname = self._parse_cpp_context(file_content, filepath)
            
            if namespace and classname:
                context = f"{namespace}::{classname}"
            elif classname:
                context = classname
            else:
                # 降级到文件名
                context = Path(filepath).stem
            
            # 缓存结果
            self.context_cache[filepath] = context
            return context
            
        except Exception as e:
            # 出错时使用文件名
            context = Path(filepath).stem
            self.context_cache[filepath] = context
            return context
    
    def _parse_cpp_context(self, content: str, filepath: str) -> Tuple[Optional[str], Optional[str]]:
        """解析 C++ 文件的命名空间和类名
        
        Args:
            content: 文件内容
            filepath: 文件路径（用于判断是 .cpp 还是 .h）
        
        Returns:
            (namespace, classname) 元组
        """
        namespace = None
        classname = None
        
        # 1. 提取类名
        # 优先从 .h 文件提取，如果是 .cpp 则尝试读取对应的 .h
        if filepath.endswith('.cpp'):
            # 尝试读取对应的 .h 文件
            h_filepath = filepath.replace('.cpp', '.h')
            try:
                h_content = self.repo.git.show(f'HEAD:{h_filepath}')
                classname = self._extract_classname(h_content)
            except:
                # .h 文件不存在，从 .cpp 提取
                classname = self._extract_classname(content)
        else:
            classname = self._extract_classname(content)
        
        # 2. 提取命名空间
        namespace = self._extract_namespace(content)
        
        # 3. 处理宏定义的命名空间（如 DCC_NAMESPACE）
        if namespace:
            namespace = self._resolve_namespace_macro(namespace, content)
        
        return namespace, classname
    
    def _extract_classname(self, content: str) -> Optional[str]:
        """从文件内容中提取类名"""
        # 匹配 class ClassName : public/private/protected BaseClass
        # 或 class ClassName {
        class_pattern = r'class\s+(\w+)\s*(?::\s*(?:public|private|protected)\s+\w+\s*)?{'
        match = re.search(class_pattern, content)
        if match:
            return match.group(1)
        return None
    
    def _extract_namespace(self, content: str) -> Optional[str]:
        """从文件内容中提取命名空间"""
        # 匹配嵌套命名空间，例如：
        # namespace DCC_NAMESPACE {
        # namespace display {
        namespaces = []
        
        # 查找所有 namespace 声明
        namespace_pattern = r'namespace\s+(\w+)\s*{'
        matches = re.finditer(namespace_pattern, content)
        
        for match in matches:
            ns = match.group(1)
            # 跳过匿名命名空间和一些常见的第三方命名空间
            if ns and ns not in ['std', 'boost', 'Qt', 'QT_BEGIN_NAMESPACE', 'QT_END_NAMESPACE']:
                namespaces.append(ns)
        
        # 返回最后两个命名空间（通常是项目命名空间和模块命名空间）
        if len(namespaces) >= 2:
            return '::'.join(namespaces[-2:])
        elif len(namespaces) == 1:
            return namespaces[0]
        
        return None
    
    def _resolve_namespace_macro(self, namespace: str, content: str) -> str:
        """解析命名空间宏定义
        
        Args:
            namespace: 可能包含宏的命名空间
            content: 文件内容
        
        Returns:
            解析后的命名空间
        """
        # 查找 #define 宏定义
        parts = namespace.split('::')
        resolved_parts = []
        
        for part in parts:
            # 检查是否是宏（通常全大写或包含下划线）
            if part.isupper() or '_' in part:
                # 尝试在文件中查找宏定义
                macro_pattern = rf'#define\s+{re.escape(part)}\s+(\w+)'
                match = re.search(macro_pattern, content)
                if match:
                    resolved_parts.append(match.group(1))
                else:
                    # 尝试从 include 的文件中查找
                    resolved = self._resolve_macro_from_includes(part, content)
                    resolved_parts.append(resolved if resolved else part)
            else:
                resolved_parts.append(part)
        
        return '::'.join(resolved_parts)
    
    def _resolve_macro_from_includes(self, macro: str, content: str) -> Optional[str]:
        """从 include 的文件中解析宏定义"""
        # 查找 #include 语句
        include_pattern = r'#include\s+["\']([^"\']+)["\']'
        includes = re.findall(include_pattern, content)
        
        for include_file in includes:
            # 只处理项目内的头文件
            if not include_file.startswith('<') and 'namespace' in include_file.lower():
                try:
                    # 尝试读取 include 的文件
                    include_content = self.repo.git.show(f'HEAD:{include_file}')
                    macro_pattern = rf'#define\s+{re.escape(macro)}\s+(\w+)'
                    match = re.search(macro_pattern, include_content)
                    if match:
                        return match.group(1)
                except:
                    continue
        
        return None
