from typing import Dict, List, Optional, Any
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from dataclasses import dataclass
import json
import logging

@dataclass
class BuildConfig:
    build_tool: str
    dependencies: List[Dict[str, str]]
    plugins: List[Dict[str, str]]
    properties: Dict[str, str]
    profiles: List[Dict[str, Any]]
    repositories: List[str]

class BuildConfigExtractor:
    def __init__(self):
        self.maven_ns = {'mvn': 'http://maven.apache.org/POM/4.0.0'}
        self._build_tool = None  # Cache for build tool type
        
        # Gradle dependency patterns
        self.gradle_dep_pattern = re.compile(
            r'(?P<config>implementation|api|compile|testImplementation|runtimeOnly)'
            r'\s*[\'"]((?P<group>[^:]+):(?P<name>[^:]+):(?P<version>[^\'"]*))[\'"]'
        )
        
        # Docker patterns
        self.dockerfile_from_pattern = re.compile(r'^FROM\s+(.+)$', re.MULTILINE)
        self.dockerfile_env_pattern = re.compile(r'^ENV\s+(\w+)\s+(.+)$', re.MULTILINE)
        self.dockerfile_run_pattern = re.compile(r'^RUN\s+(.+)$', re.MULTILINE)
        
        # Environment patterns
        self.env_var_pattern = re.compile(r'^([^=#]+)=(.*)$', re.MULTILINE)

    def get_build_tool(self) -> str:
        """
        Get the build tool type used in the project.
        Currently detects Maven or Gradle based on configuration files.
        
        Returns:
            str: The detected build tool ('maven', 'gradle', or 'unknown')
        """
        try:
            # Return cached value if available
            if self._build_tool is not None:
                return self._build_tool
            
            # Check for Maven pom.xml in current directory
            if Path('pom.xml').exists():
                self._build_tool = 'maven'
                return self._build_tool
            
            # Check for Gradle build files
            if Path('build.gradle').exists() or Path('build.gradle.kts').exists():
                self._build_tool = 'gradle'
                return self._build_tool
                
            # No recognized build tool found
            self._build_tool = 'unknown'
            return self._build_tool
            
        except Exception as e:
            logging.error(f"Error determining build tool: {str(e)}")
            return 'unknown'

    def extract_dependencies_from_pom(self, pom_path: str) -> List[Dict[str, str]]:
        """Extract dependencies from Maven pom.xml file."""
        try:
            tree = ET.parse(pom_path)
            root = tree.getroot()
            
            dependencies = []
            for dep in root.findall('.//mvn:dependency', self.maven_ns):
                group_id = dep.find('mvn:groupId', self.maven_ns)
                artifact_id = dep.find('mvn:artifactId', self.maven_ns)
                version = dep.find('mvn:version', self.maven_ns)
                scope = dep.find('mvn:scope', self.maven_ns)
                
                if group_id is not None and artifact_id is not None:
                    dependencies.append({
                        'group_id': group_id.text,
                        'artifact_id': artifact_id.text,
                        'version': version.text if version is not None else None,
                        'scope': scope.text if scope is not None else 'compile'
                    })
                    
            return dependencies
            
        except Exception as e:
            logging.error(f"Error parsing pom.xml {pom_path}: {str(e)}")
            return []

    def extract_dependencies_from_gradle(self, build_gradle_path: str) -> List[Dict[str, str]]:
        """Extract dependencies from build.gradle file."""
        try:
            content = Path(build_gradle_path).read_text(encoding='utf-8')
            dependencies = []
            
            for match in self.gradle_dep_pattern.finditer(content):
                dependencies.append({
                    'configuration': match.group('config'),
                    'group_id': match.group('group'),
                    'artifact_id': match.group('name'),
                    'version': match.group('version')
                })
                
            return dependencies
            
        except Exception as e:
            logging.error(f"Error parsing build.gradle {build_gradle_path}: {str(e)}")
            return []

    def analyze_build_config(self, project_dir: str) -> Optional[BuildConfig]:
        """Analyze build configuration files in a project directory."""
        try:
            # Check for Maven
            pom_path = Path(project_dir) / 'pom.xml'
            if pom_path.exists():
                return self._analyze_maven_config(pom_path)
                
            # Check for Gradle
            build_gradle_path = Path(project_dir) / 'build.gradle'
            if build_gradle_path.exists():
                return self._analyze_gradle_config(build_gradle_path)
                
            logging.warning(f"No recognized build configuration found in {project_dir}")
            return None
            
        except Exception as e:
            logging.error(f"Error analyzing build config in {project_dir}: {str(e)}")
            return None

    def _analyze_maven_config(self, pom_path: Path) -> BuildConfig:
        """Analyze Maven configuration from pom.xml."""
        tree = ET.parse(pom_path)
        root = tree.getroot()
        
        # Extract dependencies
        dependencies = self.extract_dependencies_from_pom(str(pom_path))
        
        # Extract plugins
        plugins = []
        for plugin in root.findall('.//mvn:plugin', self.maven_ns):
            group_id = plugin.find('mvn:groupId', self.maven_ns)
            artifact_id = plugin.find('mvn:artifactId', self.maven_ns)
            version = plugin.find('mvn:version', self.maven_ns)
            
            if group_id is not None and artifact_id is not None:
                plugins.append({
                    'group_id': group_id.text,
                    'artifact_id': artifact_id.text,
                    'version': version.text if version is not None else None
                })
        
        # Extract properties
        properties = {}
        props_elem = root.find('.//mvn:properties', self.maven_ns)
        if props_elem is not None:
            for prop in props_elem:
                tag = prop.tag.split('}')[-1]  # Remove namespace
                properties[tag] = prop.text
        
        # Extract profiles
        profiles = []
        for profile in root.findall('.//mvn:profile', self.maven_ns):
            profile_id = profile.find('mvn:id', self.maven_ns)
            if profile_id is not None:
                profiles.append({'id': profile_id.text})
        
        # Extract repositories
        repositories = []
        for repo in root.findall('.//mvn:repository', self.maven_ns):
            repo_url = repo.find('mvn:url', self.maven_ns)
            if repo_url is not None:
                repositories.append(repo_url.text)
        
        return BuildConfig(
            build_tool='maven',
            dependencies=dependencies,
            plugins=plugins,
            properties=properties,
            profiles=profiles,
            repositories=repositories
        )

    def _analyze_gradle_config(self, gradle_path: Path) -> BuildConfig:
        """Analyze Gradle configuration from build.gradle."""
        content = gradle_path.read_text(encoding='utf-8')
        
        # Extract dependencies
        dependencies = self.extract_dependencies_from_gradle(str(gradle_path))
        
        # Extract plugins (basic implementation)
        plugin_pattern = re.compile(r'apply\s+plugin:\s+[\'"]([^\'"]+)[\'"]')
        plugins = [
            {'id': match.group(1)}
            for match in plugin_pattern.finditer(content)
        ]
        
        # Extract properties (from gradle.properties if exists)
        properties = {}
        prop_file = gradle_path.parent / 'gradle.properties'
        if prop_file.exists():
            for line in prop_file.read_text(encoding='utf-8').splitlines():
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    properties[key.strip()] = value.strip()
        
        # Extract repositories
        repo_pattern = re.compile(r'maven\s*{\s*url\s+[\'"]([^\'"]+)[\'"]')
        repositories = [
            match.group(1)
            for match in repo_pattern.finditer(content)
        ]
        
        return BuildConfig(
            build_tool='gradle',
            dependencies=dependencies,
            plugins=plugins,
            properties=properties,
            profiles=[],  # Gradle doesn't have direct equivalent of Maven profiles
            repositories=repositories
        )
