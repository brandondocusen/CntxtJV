from typing import Dict, List, Optional, Set, Any
import re
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

class DocumentationType(Enum):
    README = "readme"
    API_DOC = "api_doc"
    WIKI = "wiki"
    JAVADOC = "javadoc"
    CHANGELOG = "changelog"
    CONTRIBUTING = "contributing"

@dataclass
class DocumentationSection:
    title: str
    content: str
    level: int
    subsections: List['DocumentationSection']
    metadata: Dict[str, Any]

@dataclass
class DocumentationInfo:
    doc_type: DocumentationType
    sections: List[DocumentationSection]
    overview: Optional[str]
    setup_instructions: Optional[str]
    dependencies: List[str]
    file_path: str

class DocumentationAnalyzer:
    def __init__(self):
        # Markdown patterns
        self.header_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        self.code_block_pattern = re.compile(r'```(?:\w+)?\n(.*?)\n```', re.DOTALL)
        self.link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        
        # Common documentation files
        self.doc_patterns = {
            DocumentationType.README: re.compile(r'README\.md', re.IGNORECASE),
            DocumentationType.CHANGELOG: re.compile(r'CHANGELOG\.md', re.IGNORECASE),
            DocumentationType.CONTRIBUTING: re.compile(r'CONTRIBUTING\.md', re.IGNORECASE),
            DocumentationType.API_DOC: re.compile(r'api.*\.md', re.IGNORECASE),
            DocumentationType.WIKI: re.compile(r'wiki/.*\.md', re.IGNORECASE)
        }

    def analyze_documentation(self, doc_path: str) -> Optional[DocumentationInfo]:
        """Analyze a documentation file and extract its structure and content."""
        try:
            content = Path(doc_path).read_text(encoding='utf-8')
            doc_type = self._determine_doc_type(doc_path)
            
            if not doc_type:
                return None
                
            # Extract sections and their hierarchy
            sections = self._extract_sections(content)
            
            # Extract specific components
            overview = self._extract_overview(content)
            setup_instructions = self._extract_setup_instructions(content)
            dependencies = self._extract_dependencies(content)
            
            return DocumentationInfo(
                doc_type=doc_type,
                sections=sections,
                overview=overview,
                setup_instructions=setup_instructions,
                dependencies=dependencies,
                file_path=doc_path
            )
            
        except Exception as e:
            import logging
            logging.error(f"Error analyzing documentation {doc_path}: {str(e)}")
            return None

    def _determine_doc_type(self, file_path: str) -> Optional[DocumentationType]:
        """Determine the type of documentation file."""
        file_name = Path(file_path).name
        for doc_type, pattern in self.doc_patterns.items():
            if pattern.match(file_name):
                return doc_type
        return None

    def _extract_sections(self, content: str) -> List[DocumentationSection]:
        """Extract sections and their hierarchy from markdown content."""
        sections: List[DocumentationSection] = []
        current_section = None
        section_stack = []
        
        for line in content.splitlines():
            header_match = self.header_pattern.match(line)
            if header_match:
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                
                new_section = DocumentationSection(
                    title=title,
                    content="",
                    level=level,
                    subsections=[],
                    metadata={}
                )
                
                # Manage section hierarchy
                while section_stack and section_stack[-1].level >= level:
                    section_stack.pop()
                    
                if section_stack:
                    section_stack[-1].subsections.append(new_section)
                else:
                    sections.append(new_section)
                    
                section_stack.append(new_section)
                current_section = new_section
            elif current_section is not None:
                current_section.content += line + "\n"
                
        return sections

    def _extract_overview(self, content: str) -> Optional[str]:
        """Extract project overview from documentation."""
        # Look for common overview section headers
        overview_patterns = [
            r'#+\s*Overview\s*\n(.*?)(?=\n#|$)',
            r'#+\s*Introduction\s*\n(.*?)(?=\n#|$)',
            r'#+\s*About\s*\n(.*?)(?=\n#|$)'
        ]
        
        for pattern in overview_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
                
        # If no explicit overview section, use first paragraph
        paragraphs = content.split('\n\n')
        if paragraphs:
            return paragraphs[0].strip()
            
        return None

    def _extract_setup_instructions(self, content: str) -> Optional[str]:
        """Extract setup/installation instructions from documentation."""
        setup_patterns = [
            r'#+\s*(?:Setup|Installation|Getting Started)\s*\n(.*?)(?=\n#|$)',
            r'#+\s*(?:Quick Start|Build|Deploy)\s*\n(.*?)(?=\n#|$)'
        ]
        
        for pattern in setup_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
                
        return None

    def _extract_dependencies(self, content: str) -> List[str]:
        """Extract listed dependencies from documentation."""
        dependencies = []
        
        # Look for dependencies section
        dep_section_pattern = r'#+\s*Dependencies\s*\n(.*?)(?=\n#|$)'
        dep_match = re.search(dep_section_pattern, content, re.DOTALL | re.IGNORECASE)
        
        if dep_match:
            section_content = dep_match.group(1)
            
            # Extract dependencies from lists
            list_items = re.finditer(r'[-*+]\s+([^\n]+)', section_content)
            dependencies.extend(item.group(1).strip() for item in list_items)
            
            # Extract dependencies from code blocks
            code_blocks = self.code_block_pattern.finditer(section_content)
            for block in code_blocks:
                block_content = block.group(1)
                # Common dependency formats
                dep_patterns = [
                    r'(?:implementation|compile|api)\s+[\'"]([^\'"]+)[\'"]',  # Gradle
                    r'<dependency>.*?<artifactId>(.*?)</artifactId>.*?</dependency>',  # Maven
                    r'[\w-]+==[\d.]+',  # pip
                    r'"[\w-]+"\s*:\s*"[^"]+"'  # package.json
                ]
                
                for pattern in dep_patterns:
                    deps = re.finditer(pattern, block_content, re.DOTALL)
                    dependencies.extend(dep.group(1).strip() for dep in deps)
                
        return list(set(dependencies))  # Remove duplicates

    def analyze_architecture_docs(self, content: str) -> Dict[str, Any]:
        """Extract architecture-related information from documentation."""
        architecture_info = {
            'components': [],
            'relationships': [],
            'patterns': [],
            'technologies': []
        }
        
        # Look for architecture-related sections
        arch_patterns = [
            r'#+\s*Architecture\s*\n(.*?)(?=\n#|$)',
            r'#+\s*Design\s*\n(.*?)(?=\n#|$)',
            r'#+\s*System Overview\s*\n(.*?)(?=\n#|$)'
        ]
        
        for pattern in arch_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                section = match.group(1)
                
                # Extract components
                components = re.finditer(r'[-*+]\s+(\w+)(?:\s*:\s*([^\n]+))?', section)
                architecture_info['components'].extend(
                    {'name': comp.group(1), 'description': comp.group(2).strip() if comp.group(2) else None}
                    for comp in components
                )
                
                # Extract relationships from arrows in text
                relationships = re.finditer(r'(\w+)\s*(?:->|→)\s*(\w+)', section)
                architecture_info['relationships'].extend(
                    {'from': rel.group(1), 'to': rel.group(2)}
                    for rel in relationships
                )
                
                # Extract design patterns
                patterns = re.finditer(r'(?:pattern|Pattern):\s*(\w+)', section)
                architecture_info['patterns'].extend(pat.group(1) for pat in patterns)
                
                # Extract technologies
                tech_section = re.search(r'(?:Technologies|Stack):\s*([^\n]+)', section)
                if tech_section:
                    technologies = re.findall(r'\b[\w./-]+\b', tech_section.group(1))
                    architecture_info['technologies'].extend(technologies)
                
        return architecture_info

    def extract_code_samples(self, content: str) -> List[Dict[str, str]]:
        """Extract code samples from documentation."""
        samples = []
        
        # Find all code blocks with optional language specification
        code_blocks = re.finditer(r'```(\w+)?\n(.*?)\n```', content, re.DOTALL)
        
        for block in code_blocks:
            language = block.group(1) or 'text'
            code = block.group(2)
            
            # Try to determine the purpose of the code sample
            purpose = None
            context_lines = content[:block.start()].splitlines()[-3:]  # Look at 3 lines before code block
            for line in context_lines:
                if re.search(r'example|sample|usage|how to', line, re.IGNORECASE):
                    purpose = line.strip()
                    break
                    
            samples.append({
                'language': language,
                'code': code.strip(),
                'purpose': purpose
            })
            
        return samples

    def get_coverage_threshold(self) -> float:
        """
        Get the documentation coverage threshold.
        Returns a default value of 80% as the minimum acceptable coverage.
        
        Returns:
            float: The coverage threshold percentage
        """
        return 80.0  # Default threshold of 80%
