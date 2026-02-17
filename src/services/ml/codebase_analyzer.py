"""
Codebase-Aware AI Analysis Service

This service enables the AI to analyze actual source code when investigating incidents,
providing specific file/line references and code-based suggestions.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class CodeFile:
    """Represents a code file from the repository."""
    path: str
    content: str
    language: str
    lines: int
    
    def get_snippet(self, start_line: int = 1, end_line: Optional[int] = None, context: int = 5) -> str:
        """Get a code snippet with line numbers."""
        lines = self.content.split('\n')
        end_line = end_line or len(lines)
        start = max(0, start_line - 1 - context)
        end = min(len(lines), end_line + context)
        
        snippet_lines = []
        for i, line in enumerate(lines[start:end], start=start + 1):
            marker = ">>>" if start_line <= i <= end_line else "   "
            snippet_lines.append(f"{marker} {i:4d} | {line}")
        
        return '\n'.join(snippet_lines)


@dataclass
class CodeSearchResult:
    """Result from searching the codebase."""
    file_path: str
    line_number: int
    line_content: str
    context_before: List[str]
    context_after: List[str]
    match_type: str  # 'error', 'function', 'class', 'import', 'config'


class CodebaseAnalyzer:
    """
    Analyzes codebases to provide context for incident investigation.
    
    Can connect to:
    - GitHub repositories
    - GitLab repositories
    - Local file systems
    """
    
    def __init__(
        self,
        github_token: Optional[str] = None,
        github_repo: Optional[str] = None,
        gitlab_token: Optional[str] = None,
        gitlab_repo: Optional[str] = None,
        local_path: Optional[str] = None,
    ):
        self.github_token = github_token
        self.github_repo = github_repo  # Format: "owner/repo"
        self.gitlab_token = gitlab_token
        self.gitlab_repo = gitlab_repo
        self.local_path = local_path
        self._client: Optional[httpx.AsyncClient] = None
        self._file_cache: Dict[str, CodeFile] = {}
    
    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {}
            if self.github_token:
                headers["Authorization"] = f"token {self.github_token}"
                headers["Accept"] = "application/vnd.github.v3+json"
            self._client = httpx.AsyncClient(
                base_url="https://api.github.com",
                headers=headers,
                timeout=30.0,
            )
        return self._client
    
    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def get_file(self, path: str, ref: str = "main") -> Optional[CodeFile]:
        """Fetch a file from the repository."""
        cache_key = f"{path}:{ref}"
        if cache_key in self._file_cache:
            return self._file_cache[cache_key]
        
        if self.github_repo and self.github_token:
            try:
                response = await self.client.get(
                    f"/repos/{self.github_repo}/contents/{path}",
                    params={"ref": ref},
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("type") == "file":
                        import base64
                        content = base64.b64decode(data["content"]).decode("utf-8")
                        
                        # Detect language from extension
                        ext = path.split(".")[-1] if "." in path else ""
                        lang_map = {
                            "py": "python", "js": "javascript", "ts": "typescript",
                            "java": "java", "go": "go", "rs": "rust", "rb": "ruby",
                            "yaml": "yaml", "yml": "yaml", "json": "json",
                        }
                        language = lang_map.get(ext, ext)
                        
                        code_file = CodeFile(
                            path=path,
                            content=content,
                            language=language,
                            lines=len(content.split('\n')),
                        )
                        self._file_cache[cache_key] = code_file
                        return code_file
            except Exception as e:
                logger.error(f"Failed to fetch file {path}: {e}")
        
        return None
    
    async def search_code(
        self,
        query: str,
        file_extensions: Optional[List[str]] = None,
        max_results: int = 10,
    ) -> List[CodeSearchResult]:
        """Search for code patterns in the repository."""
        results = []
        
        if self.github_repo and self.github_token:
            try:
                # Build search query
                search_query = f"{query} repo:{self.github_repo}"
                if file_extensions:
                    for ext in file_extensions:
                        search_query += f" extension:{ext}"
                
                response = await self.client.get(
                    "/search/code",
                    params={"q": search_query, "per_page": max_results},
                )
                
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("items", [])[:max_results]:
                        # Get file content for context
                        file_content = await self.get_file(item["path"])
                        if file_content:
                            # Find matching lines
                            for i, line in enumerate(file_content.content.split('\n'), 1):
                                if query.lower() in line.lower():
                                    lines = file_content.content.split('\n')
                                    results.append(CodeSearchResult(
                                        file_path=item["path"],
                                        line_number=i,
                                        line_content=line.strip(),
                                        context_before=lines[max(0, i-4):i-1],
                                        context_after=lines[i:min(len(lines), i+3)],
                                        match_type=self._classify_match(line),
                                    ))
                                    break
            except Exception as e:
                logger.error(f"Code search failed: {e}")
        
        return results
    
    async def get_service_files(
        self,
        service_name: str,
        include_tests: bool = False,
    ) -> List[CodeFile]:
        """Get all files related to a specific service."""
        files = []
        
        if self.github_repo and self.github_token:
            try:
                # Search for files containing the service name
                search_results = await self.search_code(
                    service_name,
                    file_extensions=["py", "js", "ts", "java", "go"],
                    max_results=20,
                )
                
                seen_paths = set()
                for result in search_results:
                    if result.file_path not in seen_paths:
                        if not include_tests and "test" in result.file_path.lower():
                            continue
                        file = await self.get_file(result.file_path)
                        if file:
                            files.append(file)
                            seen_paths.add(result.file_path)
            except Exception as e:
                logger.error(f"Failed to get service files: {e}")
        
        return files
    
    async def find_error_handlers(
        self,
        error_type: str,
        error_message: Optional[str] = None,
    ) -> List[CodeSearchResult]:
        """Find error handling code related to a specific error."""
        results = []
        
        # Search patterns for different error types
        patterns = [
            error_type,
            f"except {error_type}",
            f"raise {error_type}",
            f"catch.*{error_type}",
            "400" if "400" in str(error_type) else None,
            "ValidationError" if "validation" in str(error_type).lower() else None,
        ]
        
        for pattern in patterns:
            if pattern:
                search_results = await self.search_code(pattern)
                results.extend(search_results)
        
        return results[:10]  # Limit results
    
    async def analyze_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
    ) -> Dict[str, Any]:
        """Analyze a specific API endpoint."""
        analysis = {
            "endpoint": endpoint,
            "method": method,
            "route_definition": None,
            "handler_function": None,
            "related_files": [],
            "potential_issues": [],
        }
        
        # Search for route definition
        route_patterns = [
            f'@app.{method.lower()}("{endpoint}"',
            f'@router.{method.lower()}("{endpoint}"',
            f'path="{endpoint}"',
            f"'{endpoint}'",
        ]
        
        for pattern in route_patterns:
            results = await self.search_code(pattern)
            if results:
                analysis["route_definition"] = results[0]
                file = await self.get_file(results[0].file_path)
                if file:
                    analysis["related_files"].append(file)
                break
        
        return analysis
    
    def _classify_match(self, line: str) -> str:
        """Classify the type of code match."""
        line_lower = line.lower().strip()
        
        if line_lower.startswith(("def ", "async def ", "function ", "func ")):
            return "function"
        elif line_lower.startswith(("class ",)):
            return "class"
        elif "import" in line_lower or "require" in line_lower:
            return "import"
        elif "error" in line_lower or "exception" in line_lower:
            return "error"
        elif any(x in line_lower for x in ["config", "setting", "env"]):
            return "config"
        else:
            return "code"
    
    async def build_incident_context(
        self,
        incident_title: str,
        incident_description: str,
        service_name: Optional[str] = None,
        error_type: Optional[str] = None,
        endpoint: Optional[str] = None,
        error_code: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Build comprehensive codebase context for incident analysis.
        
        This is the main method used by the AI to understand the codebase
        in relation to an incident.
        """
        context = {
            "codebase_analyzed": True,
            "repository": self.github_repo,
            "relevant_files": [],
            "error_handlers": [],
            "endpoint_analysis": None,
            "potential_root_causes": [],
            "suggested_fixes": [],
            "code_snippets": [],
        }
        
        try:
            # 1. Find service-related files
            if service_name:
                logger.info(f"Searching for service files: {service_name}")
                service_files = await self.get_service_files(service_name)
                for f in service_files[:5]:  # Limit to 5 files
                    context["relevant_files"].append({
                        "path": f.path,
                        "language": f.language,
                        "lines": f.lines,
                        "preview": f.content[:500] + "..." if len(f.content) > 500 else f.content,
                    })
            
            # 2. Find error handling code
            if error_type or error_code:
                search_term = error_type or str(error_code)
                logger.info(f"Searching for error handlers: {search_term}")
                error_handlers = await self.find_error_handlers(search_term)
                for handler in error_handlers[:5]:
                    context["error_handlers"].append({
                        "file": handler.file_path,
                        "line": handler.line_number,
                        "code": handler.line_content,
                        "type": handler.match_type,
                        "context": '\n'.join(handler.context_before + [f">>> {handler.line_content}"] + handler.context_after),
                    })
            
            # 3. Analyze endpoint if provided
            if endpoint:
                logger.info(f"Analyzing endpoint: {endpoint}")
                endpoint_analysis = await self.analyze_endpoint(endpoint)
                context["endpoint_analysis"] = endpoint_analysis
            
            # 4. Search for keywords from incident
            keywords = self._extract_keywords(incident_title, incident_description)
            for keyword in keywords[:3]:
                results = await self.search_code(keyword, max_results=3)
                for r in results:
                    context["code_snippets"].append({
                        "keyword": keyword,
                        "file": r.file_path,
                        "line": r.line_number,
                        "code": r.line_content,
                        "match_type": r.match_type,
                    })
            
            logger.info(f"Built codebase context with {len(context['relevant_files'])} files, "
                       f"{len(context['error_handlers'])} error handlers, "
                       f"{len(context['code_snippets'])} code snippets")
            
        except Exception as e:
            logger.error(f"Failed to build incident context: {e}")
            context["error"] = str(e)
        
        return context
    
    def _extract_keywords(self, title: str, description: str) -> List[str]:
        """Extract relevant keywords from incident text."""
        # Common technical terms to look for
        text = f"{title} {description}".lower()
        
        # Extract service names, error types, etc.
        keywords = []
        
        # Look for service names (typically CamelCase or snake_case)
        camel_case = re.findall(r'[A-Z][a-z]+(?:[A-Z][a-z]+)+', f"{title} {description}")
        snake_case = re.findall(r'[a-z]+_[a-z]+(?:_[a-z]+)*', text)
        
        keywords.extend(camel_case)
        keywords.extend(snake_case)
        
        # Look for error codes
        error_codes = re.findall(r'\b(4\d{2}|5\d{2})\b', text)
        keywords.extend(error_codes)
        
        # Look for common error terms
        error_terms = ["error", "exception", "failed", "timeout", "connection", "validation"]
        for term in error_terms:
            if term in text:
                keywords.append(term)
        
        return list(set(keywords))[:10]


class CodebaseAwareAnalyzer:
    """
    Enhanced AI analyzer that combines LLM with codebase analysis.
    """
    
    def __init__(
        self,
        llm_provider,
        codebase_analyzer: CodebaseAnalyzer,
    ):
        self.llm = llm_provider
        self.codebase = codebase_analyzer
    
    async def analyze_incident_with_code(
        self,
        incident_title: str,
        incident_description: str,
        service_name: Optional[str] = None,
        error_type: Optional[str] = None,
        endpoint: Optional[str] = None,
        error_code: Optional[int] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform incident analysis with full codebase context.
        
        Returns analysis that includes:
        - Root cause with code references
        - Specific file/line suggestions
        - Code snippets showing the issue
        - Recommended code changes
        """
        
        # Build codebase context
        code_context = await self.codebase.build_incident_context(
            incident_title=incident_title,
            incident_description=incident_description,
            service_name=service_name,
            error_type=error_type,
            endpoint=endpoint,
            error_code=error_code,
        )
        
        # Build enhanced prompt with code context
        code_context_str = self._format_code_context(code_context)
        
        enhanced_prompt = f"""You are an expert software engineer analyzing a production incident. 
You have access to the actual codebase and should provide specific, actionable analysis.

## Incident Details
**Title:** {incident_title}
**Description:** {incident_description}
**Service:** {service_name or 'Unknown'}
**Error Type:** {error_type or 'Unknown'}
**Endpoint:** {endpoint or 'N/A'}
**Error Code:** {error_code or 'N/A'}

## Metrics
{self._format_metrics(metrics)}

## Codebase Analysis
I have analyzed the codebase ({code_context.get('repository', 'local')}) and found the following relevant code:

{code_context_str}

## Your Task
Based on the incident details AND the actual code from the repository, provide:

1. **Root Cause Analysis**: Identify the specific root cause, referencing actual files and line numbers from the codebase.

2. **Code-Based Evidence**: Point to specific code snippets that demonstrate or contribute to the issue.

3. **Recommended Fix**: Provide a specific code fix with the exact file path and suggested changes.

4. **Prevention**: Suggest code-level improvements to prevent recurrence.

Format your response as JSON with these fields:
{{
    "root_cause": "Detailed root cause with code references",
    "confidence": 0.0-1.0,
    "code_evidence": [
        {{"file": "path/to/file.py", "line": 123, "issue": "description", "code_snippet": "..."}}
    ],
    "recommended_fix": {{
        "file": "path/to/file.py",
        "description": "What to change",
        "before": "current code",
        "after": "fixed code"
    }},
    "contributing_factors": ["factor1", "factor2"],
    "prevention_suggestions": [
        {{"type": "code", "file": "path", "suggestion": "..."}}
    ]
}}
"""
        
        # Call LLM with enhanced prompt
        from src.services.ml.types import MLPrompt
        
        prompt = MLPrompt(
            task="codebase_aware_analysis",
            system_prompt="You are an expert software engineer with deep knowledge of debugging production systems. Always reference specific files and line numbers from the codebase when providing analysis.",
            user_prompt=enhanced_prompt,
        )
        
        response = await self.llm.generate(prompt)
        
        # Parse and enhance the response
        result = response.result
        if isinstance(result, str):
            import json
            try:
                result = json.loads(result)
            except:
                result = {"root_cause": result, "confidence": 0.7}
        
        # Add codebase metadata
        result["codebase_analyzed"] = True
        result["repository"] = code_context.get("repository")
        result["files_analyzed"] = len(code_context.get("relevant_files", []))
        result["code_snippets_found"] = len(code_context.get("code_snippets", []))
        
        return result
    
    def _format_code_context(self, context: Dict[str, Any]) -> str:
        """Format code context for the LLM prompt."""
        sections = []
        
        # Relevant files
        if context.get("relevant_files"):
            sections.append("### Relevant Files Found")
            for f in context["relevant_files"]:
                sections.append(f"**{f['path']}** ({f['language']}, {f['lines']} lines)")
                sections.append(f"```{f['language']}\n{f['preview']}\n```")
        
        # Error handlers
        if context.get("error_handlers"):
            sections.append("\n### Error Handling Code")
            for h in context["error_handlers"]:
                sections.append(f"**{h['file']}:{h['line']}** ({h['type']})")
                sections.append(f"```\n{h['context']}\n```")
        
        # Code snippets
        if context.get("code_snippets"):
            sections.append("\n### Related Code Snippets")
            for s in context["code_snippets"]:
                sections.append(f"**{s['file']}:{s['line']}** (keyword: {s['keyword']})")
                sections.append(f"```\n{s['code']}\n```")
        
        # Endpoint analysis
        if context.get("endpoint_analysis") and context["endpoint_analysis"].get("route_definition"):
            sections.append("\n### Endpoint Definition")
            ep = context["endpoint_analysis"]
            if ep["route_definition"]:
                r = ep["route_definition"]
                sections.append(f"**{r.file_path}:{r.line_number}**")
                sections.append(f"```\n{r.line_content}\n```")
        
        return '\n'.join(sections) if sections else "No relevant code found in the repository."
    
    def _format_metrics(self, metrics: Optional[Dict[str, Any]]) -> str:
        """Format metrics for the prompt."""
        if not metrics:
            return "No metrics available."
        
        lines = []
        for key, value in metrics.items():
            formatted_key = key.replace('_', ' ').title()
            lines.append(f"- **{formatted_key}:** {value}")
        return '\n'.join(lines)
