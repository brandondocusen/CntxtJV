from typing import List, Dict, Optional
import re
import logging


class IntegrationMapper:
    """
    A class to extract information about third-party integrations from code content.
    It focuses on API endpoints, SDK configurations, service connections,
    and patterns related to URLs, API usage, and credentials.
    """

    def __init__(self):
        # Regex patterns to identify integrations
        self.url_pattern = re.compile(
            r'(https?://[^\s\'",;]+)', re.IGNORECASE
        )
        self.api_call_pattern = re.compile(
            r'\b(client\.(?:get|post|put|delete|patch|head|options)\s*\([^\)]*\))', re.IGNORECASE
        )
        self.sdk_init_pattern = re.compile(
            r'\b(new\s+[A-Za-z_][\w\.]+Client\s*\([^\)]*\))', re.IGNORECASE
        )
        self.credentials_pattern = re.compile(
            r'\b(api_key|api_secret|client_id|client_secret|token)\b\s*[:=]\s*[\'"]?([A-Za-z0-9_\-]+)[\'"]?', re.IGNORECASE
        )
        self.service_connection_pattern = re.compile(
            r'\bDriverManager\.getConnection\s*\([^\)]*\)', re.IGNORECASE
        )

    def extract_integrations(self, content: str) -> List[Dict[str, Optional[str]]]:
        """
        Extracts integration information from the given code content.

        Args:
            content (str): The code content to analyze.

        Returns:
            List[Dict[str, Optional[str]]]: A list of dictionaries containing integration details.
        """
        integrations = []

        try:
            # Extract URLs (API endpoints)
            urls = self._extract_urls(content)
            for url in urls:
                integrations.append({
                    'type': 'api_endpoint',
                    'name': self._extract_service_name_from_url(url),
                    'details': {'url': url}
                })

            # Extract SDK configurations
            sdk_configs = self._extract_sdk_configurations(content)
            integrations.extend(sdk_configs)

            # Extract service connections
            service_connections = self._extract_service_connections(content)
            integrations.extend(service_connections)

            # Extract credentials
            credentials = self._extract_credentials(content)
            for cred in credentials:
                integrations.append({
                    'type': 'credential',
                    'name': cred['key'],
                    'details': {'value': cred['value']}
                })

        except Exception as e:
            logging.error(f"Error extracting integrations: {str(e)}")

        return integrations

    def _extract_urls(self, content: str) -> List[str]:
        """
        Extracts URLs from the code content.

        Args:
            content (str): The code content.

        Returns:
            List[str]: A list of URLs found in the content.
        """
        urls = self.url_pattern.findall(content)
        return urls

    def _extract_service_name_from_url(self, url: str) -> Optional[str]:
        """
        Attempts to extract the service name from a URL.

        Args:
            url (str): The URL to analyze.

        Returns:
            Optional[str]: The service name if identifiable.
        """
        # Simple heuristic to extract domain name
        match = re.search(r'https?://([^/]+)/?', url)
        if match:
            domain = match.group(1)
            # Remove common prefixes like 'www'
            domain = domain.replace('www.', '')
            # Extract the service name (e.g., 'api.service.com' -> 'service')
            parts = domain.split('.')
            if len(parts) >= 2:
                return parts[-2]
            return parts[0]
        return None

    def _extract_sdk_configurations(self, content: str) -> List[Dict[str, Optional[str]]]:
        """
        Extracts SDK initialization and configuration patterns.

        Args:
            content (str): The code content.

        Returns:
            List[Dict[str, Optional[str]]]: A list of SDK configurations.
        """
        sdk_configs = []
        matches = self.sdk_init_pattern.findall(content)
        for match in matches:
            sdk_configs.append({
                'type': 'sdk_configuration',
                'name': self._extract_class_name(match),
                'details': {'initialization': match}
            })
        return sdk_configs

    def _extract_class_name(self, initialization_str: str) -> Optional[str]:
        """
        Extracts the class name from an SDK initialization string.

        Args:
            initialization_str (str): The initialization string.

        Returns:
            Optional[str]: The class name if identifiable.
        """
        match = re.search(r'new\s+([\w\.]+Client)', initialization_str)
        if match:
            return match.group(1)
        return None

    def _extract_service_connections(self, content: str) -> List[Dict[str, Optional[str]]]:
        """
        Identifies service connections like database connections.

        Args:
            content (str): The code content.

        Returns:
            List[Dict[str, Optional[str]]]: A list of service connections.
        """
        connections = []
        matches = self.service_connection_pattern.findall(content)
        for match in matches:
            connections.append({
                'type': 'service_connection',
                'name': 'DatabaseConnection',
                'details': {'connection_call': match}
            })
        return connections

    def _extract_credentials(self, content: str) -> List[Dict[str, str]]:
        """
        Extracts credentials patterns from the code.

        Args:
            content (str): The code content.

        Returns:
            List[Dict[str, str]]: A list of credentials found.
        """
        credentials = []
        matches = self.credentials_pattern.findall(content)
        for key, value in matches:
            credentials.append({'key': key, 'value': value})
        return credentials
