from typing import Dict, List, Optional, Any
import re
from enum import Enum

class LogLevel(Enum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"

class LoggingAnalyzer:
    def __init__(self):
        # Common logging patterns for different Java logging frameworks
        self.log_patterns = {
            'log4j': r'(?:log|logger|LOG)\.(?P<level>trace|debug|info|warn|error|fatal)\s*\(\s*(?P<message>[^)]+)\)',
            'slf4j': r'(?:log|logger|LOG)\.(?P<level>trace|debug|info|warn|error)\s*\(\s*(?P<message>[^)]+)\)',
            'java_util': r'Logger\.(?:get)?(?:Global|getLogger)\([^)]+\)\.(?P<level>severe|warning|info|fine|finer|finest)\s*\(\s*(?P<message>[^)]+)\)',
            'system_out': r'System\.(?P<level>out|err)\.println\s*\(\s*(?P<message>[^)]+)\)'
        }
        
        # Compile patterns for better performance
        self.compiled_patterns = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in self.log_patterns.items()
        }

    def extract_logs(self, content: str) -> List[Dict[str, Any]]:
        """Extract logging statements from Java code content."""
        log_statements = []
        
        for framework, pattern in self.compiled_patterns.items():
            for match in pattern.finditer(content):
                level = match.group('level').upper()
                message = match.group('message')
                
                # Normalize log levels
                normalized_level = self._normalize_log_level(level, framework)
                
                log_statements.append({
                    'framework': framework,
                    'level': normalized_level,
                    'message': message.strip(),
                    'variables': self._extract_variables(message),
                    'pattern_type': self._identify_message_pattern(message),
                    'line_number': content[:match.start()].count('\n') + 1
                })
        
        return log_statements

    def _normalize_log_level(self, level: str, framework: str) -> str:
        """Normalize different logging levels to standard levels."""
        level_mapping = {
            'SEVERE': 'ERROR',
            'WARNING': 'WARN',
            'FINE': 'DEBUG',
            'FINER': 'DEBUG',
            'FINEST': 'TRACE',
            'OUT': 'INFO',
            'ERR': 'ERROR'
        }
        return level_mapping.get(level, level)

    def _extract_variables(self, message: str) -> List[str]:
        """Extract variables and placeholders from log messages."""
        variables = []
        
        # Look for different placeholder patterns
        placeholder_patterns = [
            r'\{(\d*)\}',           # SLF4J style
            r'%([sdfbx])',          # printf style
            r'\$\{([^}]+)\}',       # Property placeholder
            r'([a-zA-Z_]\w*)\s*\+', # String concatenation
        ]
        
        for pattern in placeholder_patterns:
            matches = re.finditer(pattern, message)
            variables.extend(match.group(1) for match in matches if match.group(1))
        
        return variables

    def _identify_message_pattern(self, message: str) -> str:
        """Identify the type of message pattern used."""
        if '{' in message and '}' in message:
            return 'placeholder'
        elif '%' in message and any(x in message for x in 'sdfbx'):
            return 'printf'
        elif '+' in message:
            return 'concatenation'
        else:
            return 'simple'

    def analyze_log_levels(self, content: str) -> Dict[str, int]:
        """Analyze distribution of log levels in the code."""
        logs = self.extract_logs(content)
        level_counts = {}
        
        for log in logs:
            level = log['level']
            level_counts[level] = level_counts.get(level, 0) + 1
            
        return level_counts

    def extract_message_patterns(self, content: str) -> Dict[str, List[str]]:
        """Extract and categorize common message patterns."""
        logs = self.extract_logs(content)
        patterns = {
            'error_patterns': [],
            'warning_patterns': [],
            'info_patterns': [],
            'debug_patterns': []
        }
        
        for log in logs:
            level = log['level']
            message = log['message']
            
            # Remove specific values but keep structure
            generalized_pattern = self._generalize_message_pattern(message)
            
            if level in ['ERROR', 'FATAL']:
                patterns['error_patterns'].append(generalized_pattern)
            elif level == 'WARN':
                patterns['warning_patterns'].append(generalized_pattern)
            elif level == 'INFO':
                patterns['info_patterns'].append(generalized_pattern)
            elif level in ['DEBUG', 'TRACE']:
                patterns['debug_patterns'].append(generalized_pattern)
                
        return patterns

    def _generalize_message_pattern(self, message: str) -> str:
        """Convert specific log message to a general pattern."""
        # Replace specific values with placeholders
        pattern = message
        pattern = re.sub(r'\{[^}]*\}', '{VAR}', pattern)
        pattern = re.sub(r'%[sdfbx]', '{VAR}', pattern)
        pattern = re.sub(r'\$\{[^}]+\}', '{PROP}', pattern)
        pattern = re.sub(r'"[^"]*"', '{STR}', pattern)
        pattern = re.sub(r'\b\d+\b', '{NUM}', pattern)
        return pattern
