from typing import Dict, List, Optional, Set
import re
import magic
from pathlib import Path
from enum import Enum
from dataclasses import dataclass

class FileType(Enum):
    TEXT = "text"
    BINARY = "binary"
    EXECUTABLE = "executable"
    ARCHIVE = "archive"
    IMAGE = "image"
    UNKNOWN = "unknown"

@dataclass
class FileInfo:
    path: str
    type: FileType
    encoding: Optional[str]
    extension: str
    purpose: str
    mime_type: str
    is_binary: bool
    header_info: Dict[str, str]

class FileTypeProcessor:
    def __init__(self):
        # File extension patterns for common Java project files
        self.file_patterns = {
            'source_code': r'\.(java|kt|groovy|scala)$',
            'build_files': r'(pom\.xml|build\.gradle|settings\.gradle)$',
            'config_files': r'\.(properties|yml|yaml|xml|json|conf|config|ini)$',
            'documentation': r'\.(md|txt|rst|adoc)$',
            'web_resources': r'\.(html|css|js|jsp|ftl)$',
            'binary_resources': r'\.(class|jar|war|ear|zip)$',
            'media_files': r'\.(jpg|jpeg|png|gif|svg|ico)$'
        }

        # Common text file headers
        self.header_patterns = {
            'package': re.compile(r'package\s+([a-zA-Z_][\w.]*)\s*;'),
            'xml_decl': re.compile(r'<\?xml\s+version="([^"]+)"\s+encoding="([^"]+)"\?>'),
            'shebang': re.compile(r'^#!(.+)$', re.MULTILINE)
        }

        # Compile extension patterns
        self.compiled_patterns = {
            purpose: re.compile(pattern, re.IGNORECASE)
            for purpose, pattern in self.file_patterns.items()
        }

    def process_file(self, file_path: str) -> FileInfo:
        """Process a file and determine its type, encoding, and purpose."""
        path = Path(file_path)
        
        try:
            # Use python-magic to detect file type and encoding
            mime_type = magic.from_file(str(path), mime=True)
            file_desc = magic.from_file(str(path))
            
            # Determine file type
            file_type = self._determine_file_type(mime_type, file_desc)
            
            # Determine if file is binary
            is_binary = file_type not in [FileType.TEXT, FileType.UNKNOWN]
            
            # Get encoding for text files
            encoding = self._detect_encoding(path) if not is_binary else None
            
            # Determine file purpose
            purpose = self._determine_purpose(path.name)
            
            # Extract header information
            header_info = self._extract_header_info(path) if not is_binary else {}
            
            return FileInfo(
                path=str(path),
                type=file_type,
                encoding=encoding,
                extension=path.suffix.lower(),
                purpose=purpose,
                mime_type=mime_type,
                is_binary=is_binary,
                header_info=header_info
            )
            
        except Exception as e:
            import logging
            logging.error(f"Error processing file {file_path}: {str(e)}")
            return FileInfo(
                path=str(path),
                type=FileType.UNKNOWN,
                encoding=None,
                extension=path.suffix.lower(),
                purpose="unknown",
                mime_type="unknown",
                is_binary=False,
                header_info={}
            )

    def _determine_file_type(self, mime_type: str, file_desc: str) -> FileType:
        """Determine file type based on MIME type and file description."""
        if mime_type.startswith('text/'):
            return FileType.TEXT
        elif 'executable' in file_desc.lower():
            return FileType.EXECUTABLE
        elif mime_type.startswith(('application/zip', 'application/x-compressed')):
            return FileType.ARCHIVE
        elif mime_type.startswith('image/'):
            return FileType.IMAGE
        elif 'ASCII' in file_desc or 'Unicode' in file_desc:
            return FileType.TEXT
        elif 'binary' in file_desc.lower():
            return FileType.BINARY
        return FileType.UNKNOWN

    def _detect_encoding(self, path: Path) -> Optional[str]:
        """Detect file encoding."""
        try:
            # Try to detect BOM
            with open(str(path), 'rb') as f:
                raw = f.read(4)
                if raw.startswith(b'\xef\xbb\xbf'):
                    return 'UTF-8-SIG'
                elif raw.startswith(b'\xff\xfe'):
                    return 'UTF-16-LE'
                elif raw.startswith(b'\xfe\xff'):
                    return 'UTF-16-BE'
                
            # Try different encodings
            for encoding in ['utf-8', 'iso-8859-1', 'ascii']:
                try:
                    with open(str(path), 'r', encoding=encoding) as f:
                        f.read()
                    return encoding
                except UnicodeDecodeError:
                    continue
                    
            return None
            
        except Exception:
            return None

    def _determine_purpose(self, filename: str) -> str:
        """Determine the purpose of the file based on its name and extension."""
        for purpose, pattern in self.compiled_patterns.items():
            if pattern.search(filename):
                return purpose
        return "unknown"

    def _extract_header_info(self, path: Path) -> Dict[str, str]:
        """Extract information from file headers."""
        header_info = {}
        
        try:
            # Read first few lines of the file
            with open(str(path), 'r', encoding='utf-8') as f:
                content = f.read(1024)  # Read first 1KB
                
            # Check for package declaration
            package_match = self.header_patterns['package'].search(content)
            if package_match:
                header_info['package'] = package_match.group(1)
                
            # Check for XML declaration
            xml_match = self.header_patterns['xml_decl'].search(content)
            if xml_match:
                header_info['xml_version'] = xml_match.group(1)
                header_info['xml_encoding'] = xml_match.group(2)
                
            # Check for shebang
            shebang_match = self.header_patterns['shebang'].search(content)
            if shebang_match:
                header_info['shebang'] = shebang_match.group(1).strip()
                
        except Exception:
            pass
            
        return header_info

    def is_generated_file(self, content: str) -> bool:
        """Detect if a file is generated."""
        generated_patterns = [
            r'@generated',
            r'DO NOT EDIT',
            r'Auto-generated',
            r'Generated by',
            r'This is a generated file'
        ]
        
        return any(re.search(pattern, content, re.IGNORECASE) 
                  for pattern in generated_patterns)
