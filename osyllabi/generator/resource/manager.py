"""
Resource manager for coordinating collection and extraction of content.

This module provides a high-level interface for managing the process of collecting
and extracting resources from various sources.
"""
import re
import importlib.util
from typing import List, Dict, Any, Optional
from pathlib import Path

from osyllabi.utils.log import log
from osyllabi.generator.resource.collector import ResourceCollector


class ResourceManager:
    """
    High-level manager for resource collection and processing.
    
    This class provides a unified interface for collecting and processing
    resources from multiple sources, with configurable options for resource
    handling and content extraction.
    """
    
    def __init__(
        self,
        max_concurrent_requests: int = 5,
        max_file_size_mb: float = 10.0,
        max_content_length: int = 10000
    ):
        """
        Initialize the resource manager.
        
        Args:
            max_concurrent_requests: Maximum number of concurrent web requests
            max_file_size_mb: Maximum file size to process in MB
            max_content_length: Maximum content length to extract
        """
        self.collector = ResourceCollector(
            max_concurrent_requests=max_concurrent_requests,
            max_file_size_mb=max_file_size_mb
        )
        self.max_content_length = max_content_length
        
        # Track overall statistics
        self.stats = {
            "sources_processed": 0,
            "total_content_size": 0,
            "keywords_extracted": 0
        }
    
    def process_sources(
        self, 
        urls: Optional[List[str]] = None, 
        paths: Optional[List[str]] = None,
        extract_keywords: bool = True,
        deduplicate: bool = True
    ) -> Dict[str, Any]:
        """
        Process resources from multiple sources.
        
        Args:
            urls: List of URLs to process
            paths: List of file/directory paths to process
            extract_keywords: Whether to extract keywords from content
            deduplicate: Whether to deduplicate similar content
            
        Returns:
            Dictionary of processed resources with metadata
        """
        urls = urls or []
        paths = paths or []
        
        log.info(f"Processing {len(urls)} URLs and {len(paths)} paths")
        
        # Collect resources
        resources = self.collector.collect(urls, paths)
        
        # Post-process resources
        if deduplicate:
            resources = self._deduplicate_resources(resources)
            
        # Truncate content if needed
        resources = self._truncate_content(resources)
        
        # Update statistics
        self.stats["sources_processed"] = len(urls) + len(paths)
        self.stats["total_content_size"] = resources["stats"].get("total_content_size", 0)
        self.stats["keywords_extracted"] = len(resources["metadata"].get("keywords", []))
        
        log.info(f"Processed {self.stats['sources_processed']} sources, "
                f"extracted {self.stats['keywords_extracted']} keywords")
        
        return resources
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get processing statistics.
        
        Returns:
            Dictionary of statistics
        """
        # Combine stats from collector with manager stats
        collector_stats = self.collector.get_stats()
        combined_stats = {**self.stats, **collector_stats}
        return combined_stats
    
    def extract_context(self, resources: Dict[str, Any], topic: str, max_items: int = 5) -> str:
        """
        Extract a unified context string from collected resources.
        
        Args:
            resources: Collected resources
            topic: Main topic for context relevance
            max_items: Maximum number of resources to include
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # Include most relevant URL content
        urls = list(resources.get("urls", {}).items())
        if urls:
            context_parts.append("## Web Resources\n")
            for i, (url, data) in enumerate(urls[:max_items]):
                title = data.get("title", url)
                content = data.get("content", "")
                if len(content) > 500:
                    content = content[:500] + "..."
                context_parts.append(f"### {title}\n{content}\n")
        
        # Include most relevant file content
        files = list(resources.get("files", {}).items())
        if files:
            context_parts.append("## Local Resources\n")
            for i, (path, data) in enumerate(files[:max_items]):
                title = data.get("title", Path(path).name)
                content = data.get("content", "")
                if len(content) > 500:
                    content = content[:500] + "..."
                context_parts.append(f"### {title}\n{content}\n")
        
        # Include keywords
        keywords = resources.get("metadata", {}).get("keywords", [])
        if keywords:
            keyword_str = ", ".join(keywords[:20])
            context_parts.append(f"## Keywords\n{keyword_str}")
            
        return "\n\n".join(context_parts)
    
    def _deduplicate_resources(self, resources: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove duplicate or very similar resources.
        
        Args:
            resources: Resources to deduplicate
            
        Returns:
            Deduplicated resources
        """
        # Separate signature sets for URLs and files
        url_signatures = set()
        file_signatures = set()
        
        # Deduplicate URLs
        unique_urls = {}
        for url, data in resources.get("urls", {}).items():
            content = data.get("content", "")
            
            # Create a simple signature (first 100 chars)
            if not content:
                continue
                
            signature = content[:100].strip().lower()
            signature = re.sub(r'\s+', ' ', signature)
            
            if signature not in url_signatures:
                unique_urls[url] = data
                url_signatures.add(signature)
        
        # Deduplicate files
        unique_files = {}
        for path, data in resources.get("files", {}).items():
            content = data.get("content", "")
            
            # Create a simple signature
            if not content:
                continue
                
            signature = content[:100].strip().lower()
            signature = re.sub(r'\s+', ' ', signature)
            
            if signature not in file_signatures:
                unique_files[path] = data
                file_signatures.add(signature)
        
        # Add deduplication statistics
        urls_removed = len(resources.get("urls", {})) - len(unique_urls)
        files_removed = len(resources.get("files", {})) - len(unique_files)
        
        # Update resources with deduplicated content
        resources["urls"] = unique_urls
        resources["files"] = unique_files
        resources["stats"]["duplicates_removed"] = urls_removed + files_removed
        
        log.debug(f"Deduplication removed {urls_removed} URL(s) and {files_removed} file(s)")
        
        return resources
    
    def _truncate_content(self, resources: Dict[str, Any]) -> Dict[str, Any]:
        """
        Truncate content that exceeds maximum length.
        
        Args:
            resources: Resources to process
            
        Returns:
            Resources with truncated content
        """
        # Truncate URL content
        for url, data in resources.get("urls", {}).items():
            content = data.get("content", "")
            if len(content) > self.max_content_length:
                data["content"] = content[:self.max_content_length] + "... [content truncated]"
                
        # Truncate file content
        for path, data in resources.get("files", {}).items():
            content = data.get("content", "")
            if len(content) > self.max_content_length:
                data["content"] = content[:self.max_content_length] + "... [content truncated]"
                
        return resources


class ResourceCollectionManager:
    """
    High-level manager for resource collection in curriculum generation.
    
    This class provides a convenient entry point to the resource collection
    functionality, delegating to the modular resource management system.
    """
    
    def __init__(
        self,
        max_concurrent_requests: int = 5,
        max_file_size_mb: float = 10.0,
        max_content_length: int = 10000
    ):
        """
        Initialize the resource collection manager.
        
        Args:
            max_concurrent_requests: Maximum number of concurrent web requests
            max_file_size_mb: Maximum file size to process in MB
            max_content_length: Maximum content length to extract
        """
        # Create the underlying resource manager
        self.manager = ResourceManager(
            max_concurrent_requests=max_concurrent_requests,
            max_file_size_mb=max_file_size_mb,
            max_content_length=max_content_length
        )
        
        # Check for optional dependencies for enhanced functionality
        self.bs4_available = importlib.util.find_spec("bs4") is not None
        self.markdown_available = importlib.util.find_spec("markdown") is not None
        self.pandas_available = importlib.util.find_spec("pandas") is not None
        self.pymupdf_available = importlib.util.find_spec("fitz") is not None
        self.docx_available = importlib.util.find_spec("docx") is not None
        
        if not self.bs4_available:
            log.warning("BeautifulSoup4 not available - HTML parsing will be limited")
        if not self.markdown_available:
            log.warning("Markdown library not available - Markdown processing will be basic")
        if not self.pandas_available:
            log.warning("Pandas not available - Data file processing will be limited")
        if not self.pymupdf_available:
            log.warning("PyMuPDF not available - PDF processing will not be available")
        if not self.docx_available:
            log.warning("python-docx not available - DOCX processing will not be available")
        
    def collect_resources(
        self,
        urls: Optional[List[str]] = None,
        paths: Optional[List[str]] = None,
        extract_keywords: bool = True,
        deduplicate: bool = True
    ) -> Dict[str, Any]:
        """
        Collect resources from URLs and file paths.
        
        Args:
            urls: List of URLs to collect from
            paths: List of file/directory paths to collect from
            extract_keywords: Whether to extract keywords from content
            deduplicate: Whether to deduplicate similar content
            
        Returns:
            Dictionary of collected resources with metadata
        """
        log.info(f"Collecting resources from {len(urls or [])} URLs and {len(paths or [])} paths")
        
        # Process sources using the resource manager
        resources = self.manager.process_sources(
            urls=urls,
            paths=paths,
            extract_keywords=extract_keywords,
            deduplicate=deduplicate
        )
        
        log.info(f"Resource collection completed: " +
                f"{len(resources.get('urls', {}))} web sources, " +
                f"{len(resources.get('files', {}))} file sources")
                
        return resources
        
    def extract_context_for_prompt(
        self,
        resources: Dict[str, Any],
        topic: str,
        max_items: int = 5
    ) -> str:
        """
        Extract a formatted context string for use in prompts.
        
        Args:
            resources: Collected resources
            topic: Main topic for relevance
            max_items: Maximum number of resources to include
            
        Returns:
            Formatted context string for prompt
        """
        # Use enhanced context extraction if markdown is available
        if self.markdown_available:
            try:
                import markdown
                
                # Extract most relevant content
                context_parts = []
                
                # Include most relevant URL content
                urls = list(resources.get("urls", {}).items())
                if urls:
                    context_parts.append("## Web Resources")
                    for i, (url, data) in enumerate(urls[:max_items]):
                        title = data.get("title", url)
                        content = data.get("content", "")
                        if len(content) > 500:
                            content = content[:500] + "..."
                        context_parts.append(f"### {title}\n{content}")
                
                # Include most relevant file content
                files = list(resources.get("files", {}).items())
                if files:
                    context_parts.append("## Local Resources")
                    for i, (path, data) in enumerate(files[:max_items]):
                        title = data.get("title", Path(path).name)
                        content = data.get("content", "")
                        if len(content) > 500:
                            content = content[:500] + "..."
                        context_parts.append(f"### {title}\n{content}")
                
                # Include keywords as markdown
                keywords = resources.get("metadata", {}).get("keywords", [])
                if keywords:
                    keyword_links = [f"[{kw}](#{kw.replace(' ', '-')})" for kw in keywords[:20]]
                    context_parts.append(f"## Keywords\n{', '.join(keyword_links)}")
                    
                # Return markdown context
                return "\n\n".join(context_parts)
            except Exception as e:
                log.warning(f"Error using markdown for context extraction: {e}")
        
        # Fall back to basic context extraction
        return self.manager.extract_context(resources, topic, max_items)
        
    def get_stats(self) -> Dict[str, Any]:
        """
        Get resource collection statistics.
        
        Returns:
            Dictionary of statistics
        """
        return self.manager.get_stats()
