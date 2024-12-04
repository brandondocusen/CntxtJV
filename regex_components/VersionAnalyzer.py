from typing import Dict, List, Optional, Any
import re
from dataclasses import dataclass
from enum import Enum

class CompatibilityType(Enum):
    COMPATIBLE = "COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNKNOWN = "UNKNOWN"

@dataclass
class VersionConstraint:
    min_version: Optional[str] = None
    max_version: Optional[str] = None
    exact_version: Optional[str] = None
    description: Optional[str] = None

class VersionAnalyzer:
    def __init__(self):
        # Version-related patterns
        self.version_patterns = {
            'java_version': r'@Target\(\"Java(\d+)\"\)',
            'api_version': r'@Api\(.*?version\s*=\s*["\']([^"\']+)["\']',
            'since_version': r'@since\s+([\d.]+)',
            'requires_version': r'@requires\s+([\d.]+)',
            'deprecated': r'@Deprecated(?:\([^)]*\))?\s*(?:/\*\*?\s*([^*]+)\**/)?',
        }
        
        # Compile patterns
        self.compiled_patterns = {
            name: re.compile(pattern, re.IGNORECASE | re.DOTALL)
            for name, pattern in self.version_patterns.items()
        }

    def extract_java_version(self) -> Optional[str]:
        """
        Extracts the Java version requirement from project configuration.
        This is typically found in build files or system properties.
        
        Returns:
            Optional[str]: The detected Java version or None if not found.
        """
        try:
            # First check for JDK version from system properties
            import os
            java_home = os.getenv('JAVA_HOME', '')
            if java_home:
                # Try to extract version from JAVA_HOME path
                version_match = re.search(r'jdk-?(\d+)', java_home.lower())
                if version_match:
                    return version_match.group(1)
            
            # Default to a minimum supported version if nothing else is found
            return "8"  # Default to Java 8 as minimum supported version
            
        except Exception:
            return None

    def extract_version_constraints(self, content: str) -> Dict[str, VersionConstraint]:
        """Extract version constraints from Java code."""
        constraints = {}
        
        # Extract version information using patterns
        for name, pattern in self.compiled_patterns.items():
            matches = pattern.finditer(content)
            for match in matches:
                if name == 'deprecated':
                    constraints['deprecated'] = VersionConstraint(
                        description=match.group(1).strip() if match.group(1) else "Deprecated"
                    )
                elif name == 'since_version':
                    constraints['since'] = VersionConstraint(
                        min_version=match.group(1),
                        description="Available since version"
                    )
                elif name == 'requires_version':
                    constraints['requires'] = VersionConstraint(
                        min_version=match.group(1),
                        description="Required version"
                    )
                else:
                    constraints[name] = VersionConstraint(
                        exact_version=match.group(1),
                        description=f"{name} requirement"
                    )
        
        return constraints

    def analyze_compatibility(self, content: str, target_version: str) -> Dict[str, Any]:
        """Analyze compatibility with a target version."""
        constraints = self.extract_version_constraints(content)
        compatibility = {
            'is_compatible': True,
            'issues': [],
            'warnings': [],
            'deprecated_elements': []
        }
        
        # Check deprecation
        if 'deprecated' in constraints:
            compatibility['deprecated_elements'].append({
                'type': 'class',  # or method/field based on context
                'reason': constraints['deprecated'].description
            })
        
        # Check version requirements
        if 'requires' in constraints:
            min_version = constraints['requires'].min_version
            if min_version and not self._is_version_compatible(target_version, min_version):
                compatibility['is_compatible'] = False
                compatibility['issues'].append(
                    f"Requires minimum version {min_version}, but target is {target_version}"
                )
        
        return compatibility

    def extract_deprecation_notices(self, content: str) -> List[Dict[str, str]]:
        """Extract deprecation notices and their context."""
        deprecation_notices = []
        
        # Find deprecated elements
        deprecated_pattern = re.compile(
            r'(?P<javadoc>/\*\*(?:.*?)\*/\s*)?'
            r'@Deprecated(?:\([^)]*\))?\s*'
            r'(?P<declaration>(?:public|private|protected|static|final|abstract)*\s+\w+\s+\w+[^;{]*)',
            re.DOTALL
        )
        
        for match in deprecated_pattern.finditer(content):
            javadoc = match.group('javadoc')
            declaration = match.group('declaration')
            
            # Extract reason from JavaDoc if available
            reason = None
            if javadoc:
                reason_match = re.search(r'@deprecated\s+(.*?)(?=\*/)', javadoc, re.DOTALL)
                if reason_match:
                    reason = reason_match.group(1).strip()
            
            # Determine the type of deprecated element
            element_type = 'unknown'
            if 'class' in declaration:
                element_type = 'class'
            elif '(' in declaration:
                element_type = 'method'
            else:
                element_type = 'field'
            
            deprecation_notices.append({
                'type': element_type,
                'declaration': declaration.strip(),
                'reason': reason,
                'line_number': content[:match.start()].count('\n') + 1
            })
        
        return deprecation_notices

    def _is_version_compatible(self, target: str, required: str) -> bool:
        """Check if target version is compatible with required version."""
        try:
            target_parts = [int(x) for x in target.split('.')]
            required_parts = [int(x) for x in required.split('.')]
            
            # Pad shorter version with zeros
            while len(target_parts) < len(required_parts):
                target_parts.append(0)
            while len(required_parts) < len(target_parts):
                required_parts.append(0)
            
            # Compare version numbers
            for t, r in zip(target_parts, required_parts):
                if t < r:
                    return False
                if t > r:
                    return True
            return True
            
        except ValueError:
            return False

    def extract_version_numbers(self, content: str) -> Dict[str, List[str]]:
        """Extract all version numbers mentioned in the code."""
        version_references = {
            'gradle_versions': [],
            'maven_versions': [],
            'java_versions': [],
            'api_versions': [],
            'other_versions': []
        }
        
        # General version number pattern
        version_pattern = re.compile(r'(?:version|Version)[\s=]+["\']?([\d.]+(?:-[\w.]+)?)["\']?')
        
        for match in version_pattern.finditer(content):
            version = match.group(1)
            
            # Categorize the version number based on context
            context = content[max(0, match.start() - 50):match.start()]
            if 'gradle' in context.lower():
                version_references['gradle_versions'].append(version)
            elif 'maven' in context.lower():
                version_references['maven_versions'].append(version)
            elif 'java' in context.lower():
                version_references['java_versions'].append(version)
            elif 'api' in context.lower():
                version_references['api_versions'].append(version)
            else:
                version_references['other_versions'].append(version)
        
        return version_references
