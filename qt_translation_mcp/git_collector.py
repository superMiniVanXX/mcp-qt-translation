"""Git history collector for translation strings"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import git
from .logger import get_logger

logger = get_logger('git_collector')


class GitCollector:
    """收集 Git 提交历史中的翻译文案"""
    
    # Qt 翻译函数的正则模式
    TR_PATTERNS = [
        # tr("text") - 基本形式
        r'tr\s*\(\s*["\']([^"\']+)["\']\s*\)',
        # tr("text", "comment") - 带注释
        r'tr\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']*)["\']\s*\)',
        # tr("text", "comment", n) - 带注释和复数形式
        r'tr\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']*)["\']\s*,\s*[^)]+\)',
        # QObject::tr("text") - 基本形式
        r'QObject::tr\s*\(\s*["\']([^"\']+)["\']\s*\)',
        # QObject::tr("text", "comment") - 带注释
        r'QObject::tr\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']*)["\']\s*\)',
        # QObject::tr("text", "comment", n) - 带注释和复数形式
        r'QObject::tr\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']*)["\']\s*,\s*[^)]+\)',
        # QCoreApplication::translate("context", "text")
        r'QCoreApplication::translate\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*\)',
        # QCoreApplication::translate("context", "text", "comment")
        r'QCoreApplication::translate\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']*)["\']\s*\)',
        # QCoreApplication::translate("context", "text", "comment", n)
        r'QCoreApplication::translate\s*\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']*)["\']\s*,\s*[^)]+\)',
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
        logger.info(f"开始收集翻译文案 - 提交范围: {commit_range}, 文件模式: {file_patterns}")
        
        translations = []
        seen = set()
        processed_commits = 0
        processed_files = 0
        processed_lines = 0
        
        # 解析提交范围，限制最大提交数防止卡死
        MAX_COMMITS = 200
        commits = list(self.repo.iter_commits(commit_range, max_count=MAX_COMMITS))
        logger.info(f"找到 {len(commits)} 个提交需要处理")
        
        for commit in commits:
            processed_commits += 1
            logger.debug(f"处理提交 {processed_commits}/{len(commits)}: {commit.hexsha[:8]} - {commit.summary}")
            
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
                
                processed_files += 1
                logger.debug(f"处理文件: {diff.b_path}")
                
                # 只处理新增的行
                if diff.diff:
                    patch = diff.diff.decode('utf-8', errors='ignore')
                    added_lines = [line[1:] for line in patch.split('\n') if line.startswith('+') and not line.startswith('+++')]
                    processed_lines += len(added_lines)
                    
                    for line in added_lines:
                        # 提取翻译文案
                        entries = self._extract_translations(line, diff.b_path)
                        for entry in entries:
                            key = (entry['context'], entry['source'])
                            if key not in seen:
                                seen.add(key)
                                translations.append(entry)
                            else:
                                logger.debug(f"跳过重复条目: [{entry['context']}] {entry['source']}")
        
        logger.info(f"收集完成 - 处理了 {processed_commits} 个提交, {processed_files} 个文件, {processed_lines} 行代码")
        logger.info(f"共收集到 {len(translations)} 个唯一的翻译条目")
        
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
        
        logger.debug(f"正在分析代码行: {line.strip()}")
        
        # 尝试匹配各种 tr 函数模式
        for pattern_idx, pattern in enumerate(self.TR_PATTERNS):
            matches = re.finditer(pattern, line)
            for match in matches:
                logger.debug(f"模式 {pattern_idx + 1} 匹配成功: {pattern}")
                logger.debug(f"匹配组: {match.groups()}")
                
                context = None
                source = None
                comment = ""
                
                if 'QCoreApplication::translate' in pattern:
                    # QCoreApplication::translate 系列
                    if len(match.groups()) >= 2:
                        context = match.group(1)
                        source = match.group(2)
                        # 如果有第三个组，那是注释
                        if len(match.groups()) >= 3 and match.group(3):
                            comment = match.group(3)
                        logger.debug(f"QCoreApplication::translate - Context: '{context}', Source: '{source}', Comment: '{comment}'")
                elif 'QObject::tr' in pattern or pattern.startswith(r'tr\s*\('):
                    # tr() 或 QObject::tr() 系列
                    source = match.group(1)
                    # 如果有第二个组，那是注释
                    if len(match.groups()) >= 2 and match.group(2):
                        comment = match.group(2)
                    # 需要从文件中提取 context
                    context = self._extract_context_from_file(filepath)
                    logger.debug(f"tr/QObject::tr - Source: '{source}', Comment: '{comment}', 提取的Context: '{context}'")
                
                if context and source:
                    entry = {
                        'context': context,
                        'source': source,
                        'comment': comment,
                        'file': filepath,
                        'line': line.strip()
                    }
                    results.append(entry)
                    logger.info(f"成功提取翻译条目: [{context}] {source}")
                    if comment:
                        logger.debug(f"  注释: {comment}")
                else:
                    logger.warning(f"提取失败 - Context: '{context}', Source: '{source}'")
        
        if not results:
            logger.debug(f"该行未匹配到翻译函数: {line.strip()}")
        
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
