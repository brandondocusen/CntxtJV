from typing import List, Dict, Optional, Any
import re
import os
import logging


class LocalizationProcessor:
    """
    A class to process localization files and extract localization information
    from code content. It focuses on mapping language files, extracting translation
    keys, and identifying locale patterns.
    """

    def __init__(self):
        # Patterns to identify localization files based on file extensions
        self.localization_file_extensions = ['.properties', '.json', '.xml', '.yml', '.yaml', '.po', '.pot', '.mo', '.resx']

        # Pattern to extract locale identifiers (e.g., en_US, fr_FR)
        self.locale_pattern = re.compile(r'\b([a-z]{2,3}(_[A-Z]{2})?)\b')

        # Patterns to extract translation keys from code (e.g., getString("key"))
        self.translation_key_patterns = [
            re.compile(r'getString\s*\(\s*"([^"]+)"\s*\)'),
            re.compile(r'getMessage\s*\(\s*"([^"]+)"\s*\)'),
            re.compile(r'resources\.getString\s*\(\s*"([^"]+)"\s*\)'),
            re.compile(r'Locale\.forLanguageTag\s*\(\s*"([^"]+)"\s*\)'),
            # Add more patterns as needed
        ]

    def extract_localizations(self, content: str) -> List[Dict[str, Any]]:
        """
        Wrapper method that combines localization extraction from code.
        
        Args:
            content (str): The code content to analyze.
            
        Returns:
            List[Dict[str, Any]]: A list of dictionaries containing localization info.
        """
        localizations = []
        
        # Extract localizations from code
        code_localizations = self.extract_localizations_from_code(content)
        
        # Transform the results into the expected format
        for loc in code_localizations:
            if loc['type'] == 'translation_key':
                localizations.append({
                    'path': loc['key'],
                    'locale': 'unknown',  # Default locale since we can't determine from key alone
                    'type': 'key_usage'
                })
            elif loc['type'] == 'locale_identifier':
                localizations.append({
                    'path': 'runtime',
                    'locale': loc['locale'],
                    'type': 'locale_definition'
                })
                
        return localizations

    def extract_localizations_from_file(self, file_path: str) -> List[Dict[str, str]]:
        """
        Extracts localization keys and values from a localization file.

        Args:
            file_path (str): The path to the localization file.

        Returns:
            List[Dict[str, str]]: A list of dictionaries containing localization keys and values.
        """
        localizations = []
        try:
            extension = os.path.splitext(file_path)[1].lower()
            if extension == '.properties':
                localizations = self._parse_properties_file(file_path)
            elif extension == '.json':
                localizations = self._parse_json_file(file_path)
            elif extension == '.xml':
                localizations = self._parse_xml_file(file_path)
            elif extension in ['.yml', '.yaml']:
                localizations = self._parse_yaml_file(file_path)
            elif extension in ['.po', '.pot']:
                localizations = self._parse_po_file(file_path)
            # Add more formats as needed
        except Exception as e:
            logging.error(f"Error processing localization file {file_path}: {str(e)}")
        return localizations

    def extract_localizations_from_code(self, content: str) -> List[Dict[str, Optional[str]]]:
        """
        Extracts localization usage patterns from code content.

        Args:
            content (str): The code content to analyze.

        Returns:
            List[Dict[str, Optional[str]]]: A list of dictionaries containing localization keys and locale identifiers.
        """
        localizations = []
        try:
            # Extract translation keys
            for pattern in self.translation_key_patterns:
                matches = pattern.findall(content)
                for key in matches:
                    localizations.append({'type': 'translation_key', 'key': key})

            # Extract locale identifiers
            locales = self.locale_pattern.findall(content)
            for locale in locales:
                locale_str = ''.join(locale)
                localizations.append({'type': 'locale_identifier', 'locale': locale_str})
        except Exception as e:
            logging.error(f"Error extracting localizations from code: {str(e)}")
        return localizations

    def _parse_properties_file(self, file_path: str) -> List[Dict[str, str]]:
        """
        Parses a .properties file to extract localization keys and values.

        Args:
            file_path (str): The path to the .properties file.

        Returns:
            List[Dict[str, str]]: A list of dictionaries with keys 'key' and 'value'.
        """
        localizations = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        localizations.append({'key': key.strip(), 'value': value.strip()})
        except Exception as e:
            logging.error(f"Error parsing properties file {file_path}: {str(e)}")
        return localizations

    def _parse_json_file(self, file_path: str) -> List[Dict[str, str]]:
        """
        Parses a JSON localization file.

        Args:
            file_path (str): The path to the JSON file.

        Returns:
            List[Dict[str, str]]: A list of dictionaries with keys 'key' and 'value'.
        """
        localizations = []
        try:
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                localizations = self._flatten_dict(data)
        except Exception as e:
            logging.error(f"Error parsing JSON file {file_path}: {str(e)}")
        return localizations

    def _parse_xml_file(self, file_path: str) -> List[Dict[str, str]]:
        """
        Parses an XML localization file.

        Args:
            file_path (str): The path to the XML file.

        Returns:
            List[Dict[str, str]]: A list of dictionaries with keys 'key' and 'value'.
        """
        localizations = []
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(file_path)
            root = tree.getroot()
            # Assuming that localization entries are in <string name="key">value</string>
            for elem in root.findall('.//string'):
                key = elem.attrib.get('name')
                value = elem.text or ''
                if key:
                    localizations.append({'key': key, 'value': value})
        except Exception as e:
            logging.error(f"Error parsing XML file {file_path}: {str(e)}")
        return localizations

    def _parse_yaml_file(self, file_path: str) -> List[Dict[str, str]]:
        """
        Parses a YAML localization file.

        Args:
            file_path (str): The path to the YAML file.

        Returns:
            List[Dict[str, str]]: A list of dictionaries with keys 'key' and 'value'.
        """
        localizations = []
        try:
            import yaml
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                localizations = self._flatten_dict(data)
        except Exception as e:
            logging.error(f"Error parsing YAML file {file_path}: {str(e)}")
        return localizations

    def _parse_po_file(self, file_path: str) -> List[Dict[str, str]]:
        """
        Parses a .po localization file.

        Args:
            file_path (str): The path to the .po file.

        Returns:
            List[Dict[str, str]]: A list of dictionaries with keys 'key' and 'value'.
        """
        localizations = []
        try:
            from polib import pofile
            po = pofile(file_path)
            for entry in po:
                key = entry.msgid
                value = entry.msgstr
                localizations.append({'key': key, 'value': value})
        except Exception as e:
            logging.error(f"Error parsing PO file {file_path}: {str(e)}")
        return localizations

    def _flatten_dict(self, data: Dict, parent_key: str = '', sep: str = '.') -> List[Dict[str, str]]:
        """
        Flattens a nested dictionary.

        Args:
            data (Dict): The dictionary to flatten.
            parent_key (str): The base key string.
            sep (str): The separator between keys.

        Returns:
            List[Dict[str, str]]: A list of key-value pairs.
        """
        items = []
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep))
            else:
                items.append({'key': new_key, 'value': str(v)})
        return items
