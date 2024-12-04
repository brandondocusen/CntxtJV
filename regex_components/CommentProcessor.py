from typing import Dict, List, Optional, Set, Any
import re
from dataclasses import dataclass
from enum import Enum

class CommentType(Enum):
    SINGLE_LINE = "single_line"
    MULTI_LINE = "multi_line"
    JAVADOC = "javadoc"
    TODO = "todo"
    FIXME = "fixme"
    DEPRECATED = "deprecated"

@dataclass
class CommentInfo:
    type: CommentType
    content: str
    line_number: int
    associated_element: Optional[str] = None
    tags: List[str] = None

class CommentProcessor:
    def __init__(self):
        # Regex patterns for different types of comments
        self.single_line_pattern = re.compile(r'//.*?$', re.MULTILINE)
        self.multi_line_pattern = re.compile(r'/\*(?!\*).*?\*/', re.DOTALL)
        self.javadoc_pattern = re.compile(r'/\*\*.*?\*/', re.DOTALL)
        
        # Patterns for special comment tags
        self.todo_pattern = re.compile(r'(?i)TODO[:\s]*(.*?)(?=\n|$)')
        self.fixme_pattern = re.compile(r'(?i)FIXME[:\s]*(.*?)(?=\n|$)')
        self.deprecated_pattern = re.compile(r'(?i)@deprecated\s*(.*?)(?=\n|\*/|$)')
        
        # Patterns for Javadoc tags
        self.javadoc_tag_pattern = re.compile(r'@(\w+)\s*(.*?)(?=@|\*/|$)', re.DOTALL)
        
        # Pattern to find the associated element (class/method/field)
        self.element_pattern = re.compile(
            r'(?:public|private|protected|static|final|native|synchronized|abstract|transient)+\s+[\w\<\>\[\]]+\s+(\w+)'
        )

    def extract_comments(self, content: str) -> List[CommentInfo]:
        """Extract all comments from Java content with their types and metadata."""
        comments = []
        
        # Track line numbers
        line_count = 1
        last_pos = 0
        
        # Process Javadoc comments first
        for match in self.javadoc_pattern.finditer(content):
            comment_text = match.group(0)
            line_number = content.count('\n', 0, match.start()) + 1
            
            # Find associated element
            next_content = content[match.end():].lstrip()
            element_match = self.element_pattern.search(next_content)
            associated_element = element_match.group(1) if element_match else None
            
            # Extract Javadoc tags
            tags = self._extract_javadoc_tags(comment_text)
            
            comments.append(CommentInfo(
                type=CommentType.JAVADOC,
                content=self._clean_comment(comment_text),
                line_number=line_number,
                associated_element=associated_element,
                tags=tags
            ))
            
            last_pos = match.end()
            line_count += comment_text.count('\n')

        # Process multi-line comments
        for match in self.multi_line_pattern.finditer(content):
            # Skip if this is actually a Javadoc comment
            if content[match.start():match.start()+3] == '/**':
                continue
                
            comment_text = match.group(0)
            line_number = content.count('\n', 0, match.start()) + 1
            
            comment_type = CommentType.MULTI_LINE
            tags = []
            
            # Check for TODO/FIXME
            if self.todo_pattern.search(comment_text):
                comment_type = CommentType.TODO
                tags.append('TODO')
            elif self.fixme_pattern.search(comment_text):
                comment_type = CommentType.FIXME
                tags.append('FIXME')
            
            comments.append(CommentInfo(
                type=comment_type,
                content=self._clean_comment(comment_text),
                line_number=line_number,
                tags=tags
            ))
            
            last_pos = match.end()
            line_count += comment_text.count('\n')

        # Process single-line comments
        for match in self.single_line_pattern.finditer(content):
            comment_text = match.group(0)
            line_number = content.count('\n', 0, match.start()) + 1
            
            comment_type = CommentType.SINGLE_LINE
            tags = []
            
            # Check for TODO/FIXME
            if self.todo_pattern.search(comment_text):
                comment_type = CommentType.TODO
                tags.append('TODO')
            elif self.fixme_pattern.search(comment_text):
                comment_type = CommentType.FIXME
                tags.append('FIXME')
            
            comments.append(CommentInfo(
                type=comment_type,
                content=self._clean_comment(comment_text),
                line_number=line_number,
                tags=tags
            ))
            
            last_pos = match.end()
            line_count += 1

        return sorted(comments, key=lambda x: x.line_number)

    def _clean_comment(self, comment: str) -> str:
        """Clean comment text by removing comment markers and extra whitespace."""
        # Remove comment markers
        comment = re.sub(r'/\*+|\*+/', '', comment)
        comment = re.sub(r'^//\s*', '', comment, flags=re.MULTILINE)
        
        # Remove leading asterisks from each line (common in multi-line comments)
        comment = re.sub(r'^\s*\*\s?', '', comment, flags=re.MULTILINE)
        
        # Clean up whitespace
        comment = re.sub(r'\s+', ' ', comment)
        return comment.strip()

    def _extract_javadoc_tags(self, comment: str) -> List[str]:
        """Extract and process Javadoc tags from comment."""
        return [match.group(1) for match in self.javadoc_tag_pattern.finditer(comment)]

    def extract_todos(self, content: str) -> List[CommentInfo]:
        """Extract all TODO comments."""
        return [
            comment for comment in self.extract_comments(content)
            if CommentType.TODO in comment.tags
        ]

    def extract_fixmes(self, content: str) -> List[CommentInfo]:
        """Extract all FIXME comments."""
        return [
            comment for comment in self.extract_comments(content)
            if CommentType.FIXME in comment.tags
        ]

    def extract_deprecated_elements(self, content: str) -> List[CommentInfo]:
        """Extract all deprecated elements with their documentation."""
        return [
            comment for comment in self.extract_comments(content)
            if any(tag.startswith('deprecated') for tag in (comment.tags or []))
        ]

    def get_documentation_coverage(self, content: str) -> Dict[str, float]:
        """Calculate documentation coverage statistics."""
        comments = self.extract_comments(content)
        javadoc_comments = [c for c in comments if c.type == CommentType.JAVADOC]
        
        # Count code elements (simplified)
        elements = len(re.findall(self.element_pattern, content))
        
        if elements == 0:
            return {'coverage_percentage': 100.0}
        
        return {
            'coverage_percentage': (len(javadoc_comments) / elements) * 100,
            'total_elements': elements,
            'documented_elements': len(javadoc_comments)
        }
