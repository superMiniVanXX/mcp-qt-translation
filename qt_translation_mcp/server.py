"""MCP Server implementation for Qt translation management"""

import os
from typing import List, Optional
from mcp.server import Server
from mcp.types import Tool, TextContent, SamplingMessage, TextContent as SamplingTextContent
from mcp.server.stdio import stdio_server

from .git_collector import GitCollector
from .ts_parser import TSParser
from .ts_updater import TSUpdater
from .translation_table import TranslationTable
from .logger import setup_logger, get_logger

# 从环境变量读取日志目录，默认为 ~/.qt_translation_mcp/logs
log_dir = os.environ.get('QT_TRANSLATION_LOG_DIR', os.path.expanduser('~/.qt_translation_mcp/logs'))
setup_logger(log_dir=log_dir)
logger = get_logger('server')

app = Server("qt-translation-mcp")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="collect_translations_from_git",
            description="从 Git 提交历史中收集需要翻译的文案。可以指定提交范围、文件路径等过滤条件。",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Git 仓库路径"
                    },
                    "commit_range": {
                        "type": "string",
                        "description": "提交范围，例如 'HEAD~10..HEAD' 或 'main..feature-branch'",
                        "default": "HEAD~10..HEAD"
                    },
                    "file_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要扫描的文件模式列表，例如 ['*.cpp', '*.h', '*.ui']",
                        "default": ["*.cpp", "*.h", "*.ui"]
                    }
                },
                "required": ["repo_path"]
            }
        ),
        Tool(
            name="parse_ts_file",
            description="解析 Qt TS 翻译文件，提取现有的翻译条目和结构信息。",
            inputSchema={
                "type": "object",
                "properties": {
                    "ts_file_path": {
                        "type": "string",
                        "description": "TS 文件路径"
                    }
                },
                "required": ["ts_file_path"]
            }
        ),
        Tool(
            name="insert_translations",
            description="将新的翻译条目插入到 TS 文件中。支持批量插入多个翻译条目到多个语言文件。",
            inputSchema={
                "type": "object",
                "properties": {
                    "ts_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要更新的 TS 文件路径列表"
                    },
                    "translations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "context": {"type": "string"},
                                "source": {"type": "string"},
                                "translation": {"type": "string"},
                                "comment": {"type": "string"}
                            },
                            "required": ["context", "source"]
                        },
                        "description": "要插入的翻译条目列表"
                    }
                },
                "required": ["ts_files", "translations"]
            }
        ),
        Tool(
            name="find_untranslated",
            description="查找 TS 文件中所有未翻译的条目。",
            inputSchema={
                "type": "object",
                "properties": {
                    "ts_file_path": {
                        "type": "string",
                        "description": "TS 文件路径"
                    }
                },
                "required": ["ts_file_path"]
            }
        ),
        Tool(
            name="export_for_translation",
            description="导出待翻译内容为表格格式，供 LLM 进行翻译。支持单语言或多语言（简体、香港繁体、台湾繁体、维吾尔语、藏语）表格。",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "数据源：'git' 从 Git 历史收集，'ts_file' 从 TS 文件的未翻译条目",
                        "enum": ["git", "ts_file"]
                    },
                    "repo_path": {
                        "type": "string",
                        "description": "Git 仓库路径（source='git' 时必需）"
                    },
                    "commit_range": {
                        "type": "string",
                        "description": "提交范围（source='git' 时使用）",
                        "default": "HEAD~10..HEAD"
                    },
                    "file_patterns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "要扫描的文件模式列表",
                        "default": ["*.cpp", "*.h", "*.ui"]
                    },
                    "ts_file_path": {
                        "type": "string",
                        "description": "TS 文件路径（source='ts_file' 时必需）"
                    },
                    "multi_language": {
                        "type": "boolean",
                        "description": "是否导出多语言表格（简体中文、香港繁体、台湾繁体、维吾尔语、藏语）",
                        "default": True
                    }
                },
                "required": ["source"]
            }
        ),
        Tool(
            name="import_translations",
            description="导入 LLM 翻译后的表格数据，填充到 TS 文件中。支持单语言或多语言表格自动识别。注意：context 名称必须与 TS 文件中的 <name> 完全一致。",
            inputSchema={
                "type": "object",
                "properties": {
                    "ts_base_path": {
                        "type": "string",
                        "description": "TS 文件基础路径（不含语言后缀），例如 '/path/to/app'，将自动处理 app_zh_CN.ts, app_zh_HK.ts, app_zh_TW.ts, app_ug.ts, app_bo.ts"
                    },
                    "translation_data": {
                        "type": "string",
                        "description": "翻译数据，Markdown 表格格式（自动识别单语言或多语言）"
                    },
                    "multi_language": {
                        "type": "boolean",
                        "description": "是否为多语言表格",
                        "default": True
                    }
                },
                "required": ["ts_base_path", "translation_data"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    logger.info(f"Tool called: {name}")
    logger.debug(f"Arguments: {arguments}")
    try:
        if name == "collect_translations_from_git":
            collector = GitCollector(arguments["repo_path"])
            commit_range = arguments.get("commit_range", "HEAD~10..HEAD")
            file_patterns = arguments.get("file_patterns", ["*.cpp", "*.h", "*.ui"])
            
            results = collector.collect_translations(commit_range, file_patterns)
            return [TextContent(
                type="text",
                text=f"收集到 {len(results)} 个需要翻译的文案：\n\n" + 
                     "\n".join([f"- {r['context']}: {r['source']}" for r in results])
            )]
        
        elif name == "parse_ts_file":
            parser = TSParser(arguments["ts_file_path"])
            entries = parser.parse()
            return [TextContent(
                type="text",
                text=f"解析完成，共 {len(entries)} 个翻译条目\n\n" +
                     f"已翻译: {sum(1 for e in entries if e.get('translated'))}\n" +
                     f"未翻译: {sum(1 for e in entries if not e.get('translated'))}"
            )]
        
        elif name == "insert_translations":
            updater = TSUpdater()
            results = updater.insert_translations(
                arguments["ts_files"],
                arguments["translations"]
            )
            return [TextContent(
                type="text",
                text=f"翻译插入完成：\n\n" + 
                     "\n".join([f"- {file}: {count} 个条目" for file, count in results.items()])
            )]
        
        elif name == "find_untranslated":
            parser = TSParser(arguments["ts_file_path"])
            entries = parser.parse()
            untranslated = [e for e in entries if not e.get("translated")]
            return [TextContent(
                type="text",
                text=f"找到 {len(untranslated)} 个未翻译条目：\n\n" +
                     "\n".join([f"- [{e['context']}] {e['source']}" for e in untranslated[:20]])
            )]
        
        elif name == "export_for_translation":
            source = arguments["source"]
            multi_language = arguments.get("multi_language", True)
            
            if source == "git":
                collector = GitCollector(arguments["repo_path"])
                commit_range = arguments.get("commit_range", "HEAD~10..HEAD")
                file_patterns = arguments.get("file_patterns", ["*.cpp", "*.h", "*.ui"])
                entries = collector.collect_translations(commit_range, file_patterns)
            else:  # ts_file
                parser = TSParser(arguments["ts_file_path"])
                all_entries = parser.parse()
                entries = [e for e in all_entries if not e.get("translated")]
            
            if multi_language:
                table = TranslationTable.create_multi_language_table(entries)
                hint = "请翻译表格中的五种语言（简体中文、香港繁体、台湾繁体、维吾尔语、藏语）"
            else:
                table = TranslationTable.create_table(entries, "中文")
                hint = "请翻译表格中的内容"
            
            return [TextContent(
                type="text",
                text=f"已导出 {len(entries)} 个待翻译条目。{hint}：\n\n{table}\n\n" +
                     f"翻译完成后，使用 import_translations 工具导入翻译结果。"
            )]
        
        elif name == "import_translations":
            translation_data = arguments["translation_data"]
            ts_base_path = arguments["ts_base_path"]
            multi_language = arguments.get("multi_language", True)
            
            logger.info(f"开始导入翻译，base_path={ts_base_path}, multi_language={multi_language}")
            logger.debug(f"翻译数据长度: {len(translation_data)} 字符")
            
            updater = TSUpdater()
            
            if multi_language:
                # 解析多语言表格
                logger.info("解析多语言表格...")
                lang_translations = TranslationTable.parse_multi_language_table(translation_data)
                
                # 记录解析结果
                for lang_code, translations in lang_translations.items():
                    logger.info(f"语言 {lang_code}: 解析到 {len(translations)} 条翻译")
                    if translations:
                        logger.debug(f"{lang_code} 前3条: {translations[:3]}")
                
                # 为每种语言生成 TS 文件路径并更新
                results = {}
                all_failed_matches = []
                
                for lang_code, translations in lang_translations.items():
                    if translations:  # 只处理有翻译内容的语言
                        ts_file = f"{ts_base_path}_{lang_code}.ts"
                        logger.info(f"更新文件 {ts_file}，共 {len(translations)} 条翻译")
                        result = updater.insert_translations([ts_file], translations)
                        results.update(result)
                        logger.info(f"文件 {ts_file} 更新完成，实际导入 {result.get(ts_file, 0)} 条")
                        
                        # 收集失败的匹配
                        if updater.last_failed_matches:
                            for failed in updater.last_failed_matches:
                                all_failed_matches.append({
                                    'file': ts_file,
                                    'lang': lang_code,
                                    **failed
                                })
                
                logger.info(f"多语言翻译导入完成，总计: {results}")
                
                # 构建返回消息
                response_text = "多语言翻译导入完成：\n\n"
                response_text += "\n".join([f"- {file}: {count} 个条目" for file, count in results.items()])
                
                # 如果有失败的匹配，添加详细信息
                if all_failed_matches:
                    response_text += f"\n\n⚠️ 有 {len(all_failed_matches)} 个条目未能匹配：\n\n"
                    for i, failed in enumerate(all_failed_matches[:10], 1):  # 最多显示10个
                        response_text += f"{i}. [{failed['lang']}] Context: `{failed['context']}`\n"
                        response_text += f"   Source: `{failed['source'][:60]}...`\n"
                        response_text += f"   原因: {failed['reason']}\n\n"
                    
                    if len(all_failed_matches) > 10:
                        response_text += f"... 还有 {len(all_failed_matches) - 10} 个失败条目\n\n"
                    
                    response_text += "请检查并修正翻译表格中的 context 名称，确保与 TS 文件中的 <name> 标签完全一致。\n"
                    response_text += "你可以使用 parse_ts_file 工具查看 TS 文件中的实际 context 名称。"
                
                return [TextContent(type="text", text=response_text)]
            else:
                # 单语言表格
                logger.info("解析单语言表格...")
                translations = TranslationTable.parse_markdown_table(translation_data)
                logger.info(f"解析到 {len(translations)} 条翻译")
                if translations:
                    logger.debug(f"前3条: {translations[:3]}")
                
                ts_file = f"{ts_base_path}_zh_CN.ts"  # 默认简体中文
                logger.info(f"更新文件 {ts_file}")
                results = updater.insert_translations([ts_file], translations)
                logger.info(f"单语言翻译导入完成: {results}")
                
                # 构建返回消息
                response_text = "翻译导入完成：\n\n"
                response_text += "\n".join([f"- {file}: {count} 个条目" for file, count in results.items()])
                
                # 如果有失败的匹配，添加详细信息
                if updater.last_failed_matches:
                    response_text += f"\n\n⚠️ 有 {len(updater.last_failed_matches)} 个条目未能匹配：\n\n"
                    for i, failed in enumerate(updater.last_failed_matches[:10], 1):
                        response_text += f"{i}. Context: `{failed['context']}`\n"
                        response_text += f"   Source: `{failed['source'][:60]}...`\n"
                        response_text += f"   原因: {failed['reason']}\n\n"
                    
                    if len(updater.last_failed_matches) > 10:
                        response_text += f"... 还有 {len(updater.last_failed_matches) - 10} 个失败条目\n\n"
                    
                    response_text += "请检查并修正翻译表格中的 context 名称，确保与 TS 文件中的 <name> 标签完全一致。\n"
                    response_text += "你可以使用 parse_ts_file 工具查看 TS 文件中的实际 context 名称。"
                
                return [TextContent(type="text", text=response_text)]
        
        else:
            return [TextContent(type="text", text=f"未知工具: {name}")]
    
    except Exception as e:
        logger.error(f"Tool execution error: {e}", exc_info=True)
        return [TextContent(type="text", text=f"错误: {str(e)}")]

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )
