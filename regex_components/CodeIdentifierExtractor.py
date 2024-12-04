from typing import Dict, List, Optional, Set, Any
import re
import logging
from dataclasses import dataclass
from enum import Enum

class ElementType(Enum):
    CLASS = "class"
    INTERFACE = "interface"
    ENUM = "enum"
    METHOD = "method"
    FIELD = "field"
    CONSTRUCTOR = "constructor"
    ANNOTATION = "annotation"

@dataclass
class Parameter:
    name: str
    type: str
    annotations: List[str]

@dataclass
class MethodInfo:
    name: str
    return_type: str
    parameters: List[Parameter]
    annotations: List[str]
    modifiers: List[str]
    is_constructor: bool

@dataclass
class ClassInfo:
    name: str
    type: ElementType
    annotations: List[str]
    modifiers: List[str]
    extends: Optional[str]
    implements: List[str]
    methods: List[MethodInfo]
    fields: List[Dict[str, Any]]

class CodeIdentifierExtractor:
    def __init__(self):
        # Regex patterns for Java code elements
        self.class_pattern = re.compile(
            r'(?P<annotations>(?:@[\w\.]+(?:\([^\)]*\))?\s*)*)'  # Changed to handle qualified annotation names
            r'\s*'
            r'(?P<modifiers>(?:public|protected|private|static|final|abstract)\s+)*'
            r'(?P<type>class|interface|enum)\s+'
            r'(?P<name>\w+)'
            r'(?:\s+extends\s+(?P<extends>[\w\.]+))?'  # Changed to handle qualified class names
            r'(?:\s+implements\s+(?P<implements>[\w\.,\s]+))?\s*'
            r'\{'
        )

        self.method_pattern = re.compile(
            r'(?P<annotations>(?:@\w+(?:\([^)]*\))?\s*)*)'
            r'\s*'  # Allow whitespace between annotations and modifiers
            r'(?P<modifiers>(?:public|private|protected|static|final|abstract|synchronized)\s+)*'
            r'(?P<return_type>[\w<>[\],\s]+)\s+'
            r'(?P<name>\w+)\s*'
            r'\((?P<parameters>[^)]*)\)\s*'
            r'(?:throws\s+[\w,\s]+)?\s*'
            r'\{'
        )

        self.field_pattern = re.compile(
            r'(?P<annotations>(?:@\w+(?:\([^)]*\))?\s*)*)'
            r'\s*'  # Allow whitespace between annotations and modifiers
            r'(?P<modifiers>(?:public|private|protected|static|final|volatile|transient)\s+)*'
            r'(?P<type>[\w<>[\],\s]+)\s+'
            r'(?P<name>\w+)\s*'
            r'(?:=\s*(?P<initializer>[^;]+))?;'
        )

        self.annotation_pattern = re.compile(r'@(\w+)(?:\([^)]*\))?')
        self.parameter_pattern = re.compile(
            r'(?P<annotations>(?:@\w+(?:\([^)]*\))?\s*)*)'
            r'(?P<type>[\w<>[\],\s]+)\s+'
            r'(?P<name>\w+)'
        )

    def extract_classes(self, content: str) -> List[ClassInfo]:
        """Extract all class, interface, and enum declarations from Java content."""
        classes = []
        for match in self.class_pattern.finditer(content):
            class_data = match.groupdict()
            class_name = class_data['name']
            
            # Get the class block content
            start_idx = match.end()
            class_block = self._extract_block_content(content[start_idx - 1:])
            
            # Process class information
            annotations = self.extract_annotations(class_data['annotations'] or '')
            modifiers = [mod for mod in (class_data['modifiers'] or '').split() if mod]
            implements = [imp.strip() for imp in (class_data['implements'] or '').split(',') if imp.strip()]
            
            # Extract methods and fields from the class block
            methods = self.extract_methods(class_block, class_name)
            fields = self.extract_fields(class_block)
            
            classes.append(ClassInfo(
                name=class_name,
                type=ElementType[class_data['type'].upper()],
                annotations=annotations,
                modifiers=modifiers,
                extends=class_data['extends'],
                implements=implements,
                methods=methods,
                fields=fields
            ))
            
        return classes

    def extract_methods(self, content: str, class_name: Optional[str] = None) -> List[MethodInfo]:
        """Extract all method declarations from Java content."""
        methods = []
        for match in self.method_pattern.finditer(content):
            method_data = match.groupdict()
            
            # Process annotations and modifiers
            annotations = self.extract_annotations(method_data['annotations'] or '')
            modifiers = [mod for mod in (method_data['modifiers'] or '').split() if mod]
            
            # Process parameters
            parameters = self._extract_parameters(method_data['parameters'])
            
            # Check if it's a constructor (name matches class name)
            is_constructor = (class_name is not None and method_data['name'] == class_name)
            
            methods.append(MethodInfo(
                name=method_data['name'],
                return_type=method_data['return_type'].strip(),
                parameters=parameters,
                annotations=annotations,
                modifiers=modifiers,
                is_constructor=is_constructor
            ))
            
        return methods

    def extract_fields(self, content: str) -> List[Dict[str, Any]]:
        """Extract all field declarations from Java content."""
        fields = []
        for match in self.field_pattern.finditer(content):
            field_data = match.groupdict()
            
            annotations = self.extract_annotations(field_data['annotations'] or '')
            modifiers = [mod for mod in (field_data['modifiers'] or '').split() if mod]
            
            fields.append({
                'name': field_data['name'],
                'type': field_data['type'].strip(),
                'annotations': annotations,
                'modifiers': modifiers,
                'initializer': field_data['initializer'].strip() if field_data['initializer'] else None
            })
            
        return fields

    def extract_annotations(self, annotations_str: str) -> List[str]:
        """Extract annotation names from a string of annotations."""
        return [match.group(1) for match in self.annotation_pattern.finditer(annotations_str)]

    def _extract_parameters(self, parameters_str: str) -> List[Parameter]:
        """Extract parameters from a method parameter string."""
        parameters = []
        if not parameters_str.strip():
            return parameters
                
        for param_match in self.parameter_pattern.finditer(parameters_str):
            param_data = param_match.groupdict()
            annotations = self.extract_annotations(param_data['annotations'] or '')
            
            parameters.append(Parameter(
                name=param_data['name'],
                type=param_data['type'].strip(),
                annotations=annotations
            ))
            
        return parameters

    def _extract_block_content(self, content: str) -> str:
        """Extract content between first { and its matching }."""
        depth = 0
        in_string = False
        in_char = False
        in_comment = False
        string_char = None
        start_pos = -1
        
        for i, char in enumerate(content):
            # Handle strings
            if char in '"\'':
                if not in_comment and not in_char:
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif string_char == char:
                        in_string = False
            
            # Handle character literals
            elif char == '`':
                if not in_comment and not in_string:
                    in_char = not in_char
                    
            # Handle comments
            elif char == '/' and i + 1 < len(content):
                if not in_string and not in_char and not in_comment:
                    if content[i + 1] == '/':
                        in_comment = True
                        
            elif char == '\n':
                in_comment = False
                
            # Handle braces
            elif not in_string and not in_char and not in_comment:
                if char == '{':
                    depth += 1
                    if depth == 1:
                        start_pos = i
                elif char == '}':
                    depth -= 1
                    if depth == 0 and start_pos != -1:
                        return content[start_pos + 1:i]
                        
        return ""  # In case of syntax error

    def get_main_class(self) -> Optional[str]:
        """
        Find the main class in a set of Java files.
        Looks for class with main method or Spring Boot application annotation.
        
        Returns:
            Optional[str]: The name of the main class if found, None otherwise
        """
        try:
            # Pattern for main class with Spring Boot annotation
            spring_boot_pattern = re.compile(
                r'@SpringBootApplication\s+public\s+class\s+(\w+)'
            )
            # Pattern for traditional Java main class
            main_method_pattern = re.compile(
                r'public\s+class\s+(\w+)(?:.*?public\s+static\s+void\s+main\s*\([^)]*\))',
                re.DOTALL
            )

            def find_main_class(content: str) -> Optional[str]:
                # First check for Spring Boot application
                spring_match = spring_boot_pattern.search(content)
                if spring_match:
                    return spring_match.group(1)
                
                # Then check for traditional main method
                main_match = main_method_pattern.search(content)
                if main_match:
                    return main_match.group(1)
                
                return None

            # Return None as we're not tracking analyzed files yet
            return None

        except Exception as e:
            logging.error(f"Error finding main class: {str(e)}")
            return None
