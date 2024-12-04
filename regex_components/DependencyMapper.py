from typing import Dict, List, Optional, Set
import re
from pathlib import Path
import xml.etree.ElementTree as ET
import json
from dataclasses import dataclass

@dataclass
class Dependency:
    group_id: str
    artifact_id: str
    version: str
    scope: Optional[str] = None

class DependencyMapper:
    def __init__(self):
        self.import_pattern = re.compile(r'import\s+(?:static\s+)?([a-zA-Z_][\w.]*\*?)\s*;')
        self.package_pattern = re.compile(r'package\s+([a-zA-Z_][\w.]*)\s*;')
        
    def extract_imports(self, content: str) -> List[str]:
        """Extract import statements from Java file content."""
        return [match.group(1) for match in self.import_pattern.finditer(content)]

    def extract_maven_dependencies(self, pom_path: str) -> List[Dependency]:
        """Extract dependencies from Maven pom.xml file."""
        try:
            tree = ET.parse(pom_path)
            root = tree.getroot()
            
            # Handle XML namespaces in Maven POM
            ns = {'mvn': 'http://maven.apache.org/POM/4.0.0'}
            dependencies = []
            
            for dep in root.findall('.//mvn:dependency', ns):
                group_id = dep.find('mvn:groupId', ns)
                artifact_id = dep.find('mvn:artifactId', ns)
                version = dep.find('mvn:version', ns)
                scope = dep.find('mvn:scope', ns)
                
                if group_id is not None and artifact_id is not None:
                    dependencies.append(Dependency(
                        group_id=group_id.text,
                        artifact_id=artifact_id.text,
                        version=version.text if version is not None else None,
                        scope=scope.text if scope is not None else 'compile'
                    ))
                    
            return dependencies
        except Exception as e:
            import logging
            logging.error(f"Error parsing pom.xml {pom_path}: {str(e)}")
            return []

    def extract_gradle_dependencies(self, build_gradle_path: str) -> List[Dependency]:
        """Extract dependencies from build.gradle file."""
        try:
            content = Path(build_gradle_path).read_text(encoding='utf-8')
            
            # Basic regex patterns for Gradle dependency declarations
            dependency_pattern = re.compile(
                r'(?:implementation|compile|api|testImplementation|testCompile)'
                r'\s*[\'"]([^:]+):([^:]+):([^\'"]+)[\'"]'
            )
            
            dependencies = []
            for match in dependency_pattern.finditer(content):
                group_id, artifact_id, version = match.groups()
                dependencies.append(Dependency(
                    group_id=group_id,
                    artifact_id=artifact_id,
                    version=version,
                    scope='compile'  # Default scope for Gradle
                ))
                
            return dependencies
        except Exception as e:
            import logging
            logging.error(f"Error parsing build.gradle {build_gradle_path}: {str(e)}")
            return []

    def map_import_hierarchy(self, imports: List[str]) -> Dict[str, List[str]]:
        """Create a hierarchy map of imports."""
        hierarchy: Dict[str, List[str]] = {}
        
        for imp in imports:
            parts = imp.split('.')
            current_level = hierarchy
            
            for i, part in enumerate(parts[:-1]):
                if part not in current_level:
                    current_level[part] = {}
                current_level = current_level[part]
                
            if parts[-1] != '*':
                if 'classes' not in current_level:
                    current_level['classes'] = []
                current_level['classes'].append(parts[-1])
                
        return hierarchy

    def extract_environment_variables(self, content: str) -> Set[str]:
        """Extract environment variable references from code."""
        env_patterns = [
            re.compile(r'System\.getenv\([\'"](\w+)[\'"]\)'),
            re.compile(r'@Value\(\s*[\'"]?\$\{([^}]+)}[\'"]?\s*\)'),
            re.compile(r'environment\.get\([\'"](\w+)[\'"]\)')
        ]
        
        env_vars = set()
        for pattern in env_patterns:
            env_vars.update(match.group(1) for match in pattern.finditer(content))
            
        return env_vars
