from typing import Dict, List, Optional
import re
import os
from pathlib import Path
import configparser
import json
from dataclasses import dataclass
from enum import Enum
import logging

class ConfigType(Enum):
    ENV = '.env'
    INI = '.ini'
    PROPERTIES = '.properties'
    XML = '.xml'
    YAML = '.yml'
    JSON = '.json'

@dataclass
class ParsedConfig:
    config_type: ConfigType
    key_values: Dict[str, str]
    sections: Dict[str, Dict[str, str]]
    imports: List[str]
    file_relations: List[str]

class ConfigFileParser:
    def __init__(self):
        self.package_pattern = re.compile(r'package\s+([a-zA-Z_][\w.]*)\s*;')
        self.import_pattern = re.compile(r'import\s+(?:static\s+)?([a-zA-Z_][\w.]*\*?)\s*;')
        self.property_pattern = re.compile(r'([^=\s]+)\s*=\s*([^\n]+)')
        self.xml_prop_pattern = re.compile(r'<([^/>]+)>([^<]+)</\1>')
        
    def extract_package(self, content: str) -> Optional[str]:
        """Extract package name from Java file content."""
        match = self.package_pattern.search(content)
        return match.group(1) if match else None

    def parse_config_file(self, file_path: str) -> Optional[ParsedConfig]:
        """Parse various config file types and extract key information."""
        try:
            file_type = Path(file_path).suffix.lower()
            content = Path(file_path).read_text(encoding='utf-8')
            
            if file_type == '.env':
                return self._parse_env(content)
            elif file_type == '.ini':
                return self._parse_ini(file_path)
            elif file_type == '.properties':
                return self._parse_properties(content)
            elif file_type == '.xml':
                return self._parse_xml(content)
            elif file_type in ['.yml', '.yaml']:
                return self._parse_yaml(content)
            elif file_type == '.json':
                return self._parse_json(content)
            return None
        except Exception as e:
            logging.error(f"Error parsing config file {file_path}: {str(e)}")
            return None

    def _parse_env(self, content: str) -> ParsedConfig:
        """Parse .env file content."""
        key_values = {}
        for match in self.property_pattern.finditer(content):
            key, value = match.groups()
            key_values[key.strip()] = value.strip()
        
        return ParsedConfig(
            config_type=ConfigType.ENV,
            key_values=key_values,
            sections={},
            imports=[],
            file_relations=[]
        )

    def _parse_ini(self, file_path: str) -> ParsedConfig:
        """Parse .ini file content."""
        config = configparser.ConfigParser()
        config.read(file_path)
        
        sections = {}
        for section in config.sections():
            sections[section] = dict(config[section])
            
        return ParsedConfig(
            config_type=ConfigType.INI,
            key_values=dict(config.defaults()),
            sections=sections,
            imports=[],
            file_relations=[]
        )

    def _parse_properties(self, content: str) -> ParsedConfig:
        """Parse Java .properties file content."""
        key_values = {}
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    key_values[key.strip()] = value.strip()
                    
        return ParsedConfig(
            config_type=ConfigType.PROPERTIES,
            key_values=key_values,
            sections={},
            imports=[],
            file_relations=[]
        )

    def _parse_xml(self, content: str) -> ParsedConfig:
        """Parse XML configuration file content."""
        key_values = {}
        for match in self.xml_prop_pattern.finditer(content):
            key, value = match.groups()
            key_values[key.strip()] = value.strip()
            
        return ParsedConfig(
            config_type=ConfigType.XML,
            key_values=key_values,
            sections={},
            imports=[],
            file_relations=[]
        )

    def _parse_yaml(self, content: str) -> ParsedConfig:
        """Parse YAML configuration file content."""
        try:
            import yaml
            data = yaml.safe_load(content)
            return ParsedConfig(
                config_type=ConfigType.YAML,
                key_values=self._flatten_dict(data),
                sections={},
                imports=[],
                file_relations=[]
            )
        except ImportError:
            logging.warning("PyYAML not installed. YAML parsing unavailable.")
            return None

    def _parse_json(self, content: str) -> ParsedConfig:
        """Parse JSON configuration file content."""
        data = json.loads(content)
        return ParsedConfig(
            config_type=ConfigType.JSON,
            key_values=self._flatten_dict(data),
            sections={},
            imports=[],
            file_relations=[]
        )

    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '.') -> Dict[str, str]:
        """Flatten nested dictionary with dot notation."""
        items: List = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, str(v)))
        return dict(items)
