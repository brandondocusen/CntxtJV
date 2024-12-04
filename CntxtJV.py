# CntxtJV.py - Java codebase analyzer that generates comprehensive knowledge graphs optimized for LLM context windows

import os
import sys
import json
import networkx as nx
from networkx.readwrite import json_graph
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
import logging
from datetime import datetime

# Import regex modules
try:
    from regex_components.ConfigFileParser import ConfigFileParser
    from regex_components.DependencyMapper import DependencyMapper
    from regex_components.CodeIdentifierExtractor import CodeIdentifierExtractor, MethodInfo, Parameter
    from regex_components.CommentProcessor import CommentProcessor
    from regex_components.DocumentationAnalyzer import DocumentationAnalyzer
    from regex_components.BuildConfigExtractor import BuildConfigExtractor
    from regex_components.LoggingAnalyzer import LoggingAnalyzer
    from regex_components.VersionAnalyzer import VersionAnalyzer
    from regex_components.FileTypeProcessor import FileTypeProcessor
    from regex_components.IntegrationMapper import IntegrationMapper
    from regex_components.LocalizationProcessor import LocalizationProcessor
    from regex_components.CommentProcessor import CommentInfo, CommentType
except ImportError as e:
    print(f"Error importing regex components: {str(e)}")
    print("Make sure all component files are in the 'regex_components' directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class JavaCodeKnowledgeGraph:
    def __init__(self, directory: str):
        """Initialize the knowledge graph generator."""
        self.directory = directory
        self.graph = nx.DiGraph()
        self.files_processed = 0
        self.total_files = 0
        self.dirs_processed = 0
        self.analyzed_files = set()
        self.class_map = {}

        # Initialize statistics
        self.stats = {
            'total_classes': 0,
            'total_interfaces': 0,
            'total_enums': 0,
            'total_methods': 0,
            'total_packages': set(),
            'total_imports': 0,
            'total_dependencies': set(),
            'total_annotations': set(),
            'total_api_endpoints': 0,
            'total_logging_statements': 0,
            'files_with_errors': 0,
            'total_comments': 0,
            'total_configs': 0,
            'total_integrations': 0,
            'total_localizations': 0,
            'total_build_scripts': 0,
            'total_version_constraints': 0
        }

        # Initialize processors and ignored paths
        self._init_processors()
        self._init_ignored_paths()

    def _init_processors(self):
        """Initialize all component processors."""
        try:
            self.config_parser = ConfigFileParser()
            self.dependency_mapper = DependencyMapper()
            self.code_extractor = CodeIdentifierExtractor()
            self.comment_processor = CommentProcessor()
            self.doc_analyzer = DocumentationAnalyzer()
            self.build_extractor = BuildConfigExtractor()
            self.log_analyzer = LoggingAnalyzer()
            self.version_analyzer = VersionAnalyzer()
            self.file_processor = FileTypeProcessor()
            self.integration_mapper = IntegrationMapper()
            self.localization_processor = LocalizationProcessor()
        except Exception as e:
            logging.error(f"Error initializing processors: {str(e)}")
            raise

    def _init_ignored_paths(self):
        """Initialize sets of ignored directories and files."""
        self.ignored_directories = {
            'target', 'bin', 'build', '.git', '.idea', '.settings',
            '.gradle', '.classpath', '.project', '.metadata', '.vscode',
            '__pycache__', '.DS_Store', 'out', 'logs', 'tmp', 'temp',
            'test-output', '.mvn', '.svn'
        }

        self.ignored_files = {
            '.gitignore', '.classpath', '.project', '.DS_Store'
        }

    def _add_dependency_node(self, build_node: str, dep_info: Dict[str, str]):
        """Add a dependency node to the graph."""
        dep_id = f"{dep_info['group_id']}:{dep_info['artifact_id']}"
        dep_node = f"Dependency: {dep_id}"
        if not self.graph.has_node(dep_node):
            self.graph.add_node(
                dep_node,
                type="dependency",
                group_id=dep_info['group_id'],
                artifact_id=dep_info['artifact_id'],
                version=dep_info.get('version', ''),
                scope=dep_info.get('scope', 'compile'),
                id=dep_node
            )
            self.stats['total_dependencies'].add(dep_id)
        self.graph.add_edge(build_node, dep_node, relation="DEPENDS_ON")

    def analyze_codebase(self):
        """Analyze the Java codebase and build the knowledge graph."""
        logging.info("Starting codebase analysis...")

        # Count files first
        self._count_files()

        # Process the codebase
        self._process_codebase()

        logging.info(f"Completed analysis of {self.files_processed} files")
        if self.stats['files_with_errors'] > 0:
            logging.warning(f"Encountered errors in {self.stats['files_with_errors']} files")

    def _count_files(self):
        """Count total files to be processed."""
        for root, dirs, files in os.walk(self.directory):
            dirs[:] = [d for d in dirs if d not in self.ignored_directories]

            if not any(ignored in root.split(os.sep) for ignored in self.ignored_directories):
                self.total_files += sum(
                    1 for f in files
                    if f.endswith(".java") and f not in self.ignored_files
                )
                # Include build files
                self.total_files += sum(
                    1 for f in files
                    if f in {"pom.xml", "build.gradle"} and f not in self.ignored_files
                )
                # Include config files
                self.total_files += sum(
                    1 for f in files
                    if f.endswith((".ini", ".env", ".yml", ".yaml", ".properties", ".json")) and f not in self.ignored_files
                )
                # Include localization files
                self.total_files += sum(
                    1 for f in files
                    if f.startswith("messages_") and f.endswith(".properties") and f not in self.ignored_files
                )
                # Include README and documentation files
                self.total_files += sum(
                    1 for f in files
                    if f.lower() in {"readme.md", "api.md", "docs.md"} and f not in self.ignored_files
                )

        logging.info(f"Found {self.total_files} files to process")

    def _process_codebase(self):
        """Process all files in the codebase."""
        for root, dirs, files in os.walk(self.directory):
            dirs[:] = [d for d in dirs if d not in self.ignored_directories]

            if any(ignored in root.split(os.sep) for ignored in self.ignored_directories):
                continue

            rel_path = os.path.relpath(root, self.directory)
            self.dirs_processed += 1
            logging.debug(f"Processing directory [{self.dirs_processed}]: {rel_path}")

            for file in files:
                if file in self.ignored_files:
                    continue

                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, self.directory)

                if file.endswith(".java"):
                    self._process_java_file(file_path)
                elif file in {"pom.xml", "build.gradle"}:
                    self._process_build_file(file_path)
                elif file.endswith((".ini", ".env", ".yml", ".yaml", ".properties", ".json")):
                    self._process_config_file(file_path)
                elif file.startswith("messages_") and file.endswith(".properties"):
                    self._process_localization_file(file_path)
                elif file.lower() in {"readme.md", "api.md", "docs.md"}:
                    self._process_documentation_file(file_path)
                else:
                    self._process_generic_file(file_path)

    def _process_java_file(self, file_path: str):
        """Process a single Java file."""
        if file_path in self.analyzed_files:
            return

        try:
            self.files_processed += 1
            relative_path = os.path.relpath(file_path, self.directory)
            logging.debug(f"Processing file [{self.files_processed}/{self.total_files}]: {file_path}")

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Add file node
            file_node = f"File: {relative_path}"
            self.analyzed_files.add(file_path)
            self.graph.add_node(file_node, type="file", path=relative_path, encoding="UTF-8", fileType="SOURCE_CODE")

            # Process file contents
            self._process_file_contents(file_node, content, file_path)

        except Exception as e:
            logging.error(f"Error processing {file_path}: {str(e)}")
            self.stats['files_with_errors'] += 1

    def _process_file_contents(self, file_node: str, content: str, file_path: str):
        """Process the contents of a Java file using all analyzers."""
        try:
            # Extract and process package
            package_name = self.config_parser.extract_package(content)
            if package_name:
                self._add_package_node(file_node, package_name)

            # Process imports
            imports = self.dependency_mapper.extract_imports(content)
            for import_name in imports:
                self._add_import_node(file_node, import_name)

            # Process classes, interfaces, enums
            classes = self.code_extractor.extract_classes(content)
            for class_info in classes:
                class_name = class_info.name
                class_type = str(class_info.type).capitalize()
                self._add_class_node(file_node, class_name, class_type)
                logging.debug(f"Extracted classes: {classes}")
                logging.debug(f"Class extracted: {class_name} of type {class_type}")

                # Add class annotations
                for annotation in class_info.annotations:
                    self._add_annotation_node(file_node, annotation)

                # Process methods within the class
                for method in class_info.methods:
                    self._add_method_node(class_name, method)
                    # Add method annotations
                    for annotation in method.annotations:
                        self._add_annotation_node(file_node, annotation)

            # Process comments and documentation
            comments = self.comment_processor.extract_comments(content)
            for comment in comments:
                self._add_comment_node(file_node, comment)

            # Process logging statements
            logging_statements = self.log_analyzer.extract_logs(content)
            for log in logging_statements:
                self._add_log_statement_node(file_node, log)

            # Process integrations
            integrations = self.integration_mapper.extract_integrations(content)
            for integration in integrations:
                self._add_integration_node(file_node, integration)

            # Process version constraints
            version_info = self.version_analyzer.extract_version_constraints(content)
            if version_info:
                self._add_version_info(file_node, version_info)

            # Process localization usage
            localizations = self.localization_processor.extract_localizations(content)
            for localization in localizations:
                self._add_localization_usage_node(file_node, localization)

        except Exception as e:
            logging.error(f"Error in _process_file_contents for {file_node}: {str(e)}")
            raise

    def _add_package_node(self, file_node: str, package_name: str):
        """Add a package node to the graph."""
        package_node = f"Package: {package_name}"
        if not self.graph.has_node(package_node):
            self.graph.add_node(package_node, type="package", name=package_name, id=package_node)
            self.stats['total_packages'].add(package_name)
        self.graph.add_edge(package_node, file_node, relation="CONTAINS_FILE")

    def _add_import_node(self, file_node: str, import_name: str):
        """Add an import node to the graph."""
        import_node = f"Import: {import_name}"
        if not self.graph.has_node(import_node):
            self.graph.add_node(import_node, type="import", name=import_name, id=import_node)
            self.stats['total_imports'] += 1
            logging.debug(f"Import added: {import_name}, Total imports: {self.stats['total_imports']}")
        self.graph.add_edge(file_node, import_node, relation="IMPORTS")
        logging.debug(f"Edge added: {file_node} -> {import_node} with relation IMPORTS")


    def _add_class_node(self, file_node: str, class_name: str, class_type: str):
        """Add a class node to the graph."""
        class_type = class_type.strip().lower()
        # Map Elementtype.class to class
        if class_type == 'elementtype.class':
            class_type = 'class'

        class_node = f"{class_type.capitalize()}: {class_name}"
        if not self.graph.has_node(class_node):
            self.graph.add_node(class_node, type=class_type, name=class_name, id=class_node)
            logging.debug(f"Class node added: {class_node} of type {class_type}")

            # Increment counters for classes, interfaces, enums
            class_types = {'class': 'total_classes', 'interface': 'total_interfaces', 'enum': 'total_enums'}
            if class_type in class_types:
                self.stats[class_types[class_type]] += 1
                logging.debug(f"Updated {class_types[class_type]} to {self.stats[class_types[class_type]]}")
            else:
                logging.warning(f"Unknown class type: {class_type}")
        else:
            logging.debug(f"Class node already exists: {class_node}")
        
        self.graph.add_edge(file_node, class_node, relation="DEFINES")
        logging.debug(f"Edge added: {file_node} -> {class_node} with relation DEFINES")

    def _add_method_node(self, class_name: str, method_info: MethodInfo):
        """Add a method node to the graph."""
        method_name = method_info.name
        method_node = f"Method: {method_name}"
        
        if not self.graph.has_node(method_node):
            # Convert parameters to a serializable format
            parameters = [
                {
                    'name': param.name,
                    'type': param.type,
                    'annotations': param.annotations
                }
                for param in method_info.parameters
            ]
            
            self.graph.add_node(
                method_node,
                type="method",
                name=method_name,
                id=method_node,
                return_type=method_info.return_type,
                parameters=parameters,
                annotations=method_info.annotations,
                modifiers=method_info.modifiers,
                is_constructor=method_info.is_constructor
            )
            self.stats['total_methods'] += 1
            logging.debug(f"Method node added: {method_node}, Total methods: {self.stats['total_methods']}")
        else:
            logging.debug(f"Method node already exists: {method_node}")

        # Link method to its class
        class_node = f"Class: {class_name}"
        if self.graph.has_node(class_node):
            self.graph.add_edge(class_node, method_node, relation="HAS_METHOD")
            logging.debug(f"Edge added: {class_node} -> {method_node} with relation HAS_METHOD")
        else:
            logging.warning(f"Class node {class_node} does not exist; cannot add method {method_info.name}")


    def _add_annotation_node(self, file_node: str, annotation: str):
        """Add an annotation node to the graph."""
        annotation_node = f"Annotation: {annotation}"
        
        if not self.graph.has_node(annotation_node):
            self.graph.add_node(annotation_node, type="annotation", name=annotation, id=annotation_node)
            if annotation not in self.stats['total_annotations']:
                self.stats['total_annotations'].add(annotation)
                logging.debug(f"Annotation node added: {annotation_node}, Total unique annotations: {len(self.stats['total_annotations'])}")
        else:
            logging.debug(f"Annotation node already exists: {annotation_node}")

        self.graph.add_edge(file_node, annotation_node, relation="ANNOTATED_WITH")
        logging.debug(f"Edge added: {file_node} -> {annotation_node} with relation ANNOTATED_WITH")

    def _add_comment_node(self, file_node: str, comment: CommentInfo):
        """Add a comment node to the graph."""
        comment_id = f"Comment: {comment.line_number}_{hash(comment.content)}"
        comment_node = comment_id
        if not self.graph.has_node(comment_node):
            self.graph.add_node(
                comment_node,
                type="comment",
                comment_type=comment.type.value,
                content=comment.content,
                line_number=comment.line_number,
                associated_element=comment.associated_element,
                tags=comment.tags or [],
                id=comment_node
            )
            self.stats['total_comments'] += 1
        self.graph.add_edge(file_node, comment_node, relation="HAS_COMMENT")

    def _add_log_statement_node(self, file_node: str, log_info: Dict[str, Any]):
        """Add a log statement node to the graph."""
        log_id = f"Log: {hash(log_info.get('message', ''))}"
        log_node = log_id
        if not self.graph.has_node(log_node):
            self.graph.add_node(
                log_node,
                type="log_statement",
                level=log_info.get('level', 'INFO'),
                message=log_info.get('message', ''),
                id=log_node
            )
            self.stats['total_logging_statements'] += 1
        self.graph.add_edge(file_node, log_node, relation="USES")

    def _add_integration_node(self, file_node: str, integration: Dict[str, Any]):
        """Add an integration node to the graph."""
        integration_name = integration.get('name', 'unnamed_integration')
        integration_node = f"Integration: {integration_name}"
        if not self.graph.has_node(integration_node):
            self.graph.add_node(
                integration_node,
                type="api_integration",
                name=integration_name,
                url=integration.get('url', ''),
                id=integration_node
            )
            self.stats['total_integrations'] += 1
        self.graph.add_edge(file_node, integration_node, relation="INTEGRATES_WITH")

    def _add_version_info(self, file_node: str, version_info: Dict[str, Any]):
        """Add version information to the graph."""
        for version_type, version_data in version_info.items():
            version_node = f"Version: {version_type}"
            if not self.graph.has_node(version_node):
                self.graph.add_node(
                    version_node,
                    type="version",
                    version_type=version_type,
                    constraints=version_data.get('constraints', ''),
                    id=version_node
                )
                self.stats['total_version_constraints'] += 1
            self.graph.add_edge(file_node, version_node, relation="HAS_VERSION")

    def _add_localization_usage_node(self, file_node: str, localization: Dict[str, Any]):
        """Add a localization usage node to the graph."""
        localization_path = localization.get('path', 'unknown_path')
        locale = localization.get('locale', 'unknown_locale')
        localization_node = f"i18n: {os.path.splitext(os.path.basename(localization_path))[0]}"
        if not self.graph.has_node(localization_node):
            self.graph.add_node(
                localization_node,
                type="localization",
                path=localization_path,
                locale=locale,
                id=localization_node
            )
            self.stats['total_localizations'] += 1
        self.graph.add_edge(file_node, localization_node, relation="USES")

    def _process_build_file(self, file_path: str):
        """Process build configuration files."""
        try:
            build_type = "maven" if file_path.endswith("pom.xml") else "gradle"
            dependencies = []
            if build_type == "maven":
                dependencies = self.dependency_mapper.extract_maven_dependencies(file_path)
            else:  # gradle
                dependencies = self.dependency_mapper.extract_gradle_dependencies(file_path)

            # Add build script node
            build_node = f"Build: {os.path.relpath(file_path, self.directory)}"
            if not self.graph.has_node(build_node):
                self.graph.add_node(
                    build_node,
                    type="build_script",
                    path=os.path.relpath(file_path, self.directory),
                    build_tool=build_type.capitalize(),
                    id=build_node
                )
                self.stats['total_build_scripts'] += 1

            for dep in dependencies:
                dep_info = {
                    'group_id': dep.group_id,
                    'artifact_id': dep.artifact_id,
                    'version': dep.version,
                    'scope': dep.scope
                }
                self._add_dependency_node(build_node, dep_info)

        except Exception as e:
            logging.error(f"Error processing build file {file_path}: {str(e)}")
            self.stats['files_with_errors'] += 1

    def _process_config_file(self, file_path: str):
        """Process configuration files."""
        try:
            relative_path = os.path.relpath(file_path, self.directory)
            config_info = self.config_parser.parse_config_file(file_path)
            if config_info:
                config_node = f"Config: {relative_path}"
                if not self.graph.has_node(config_node):
                    self.graph.add_node(
                        config_node,
                        type="config",
                        path=relative_path,
                        environment=config_info.config_type.value,
                        id=config_node
                    )
                    self.stats['total_configs'] += 1
                # Link config to file
                file_node = f"File: {relative_path}"
                self.graph.add_edge(file_node, config_node, relation="CONFIGURED_BY")
        except AttributeError as ae:
            logging.error(f"AttributeError processing config file {file_path}: {str(ae)}")
            self.stats['files_with_errors'] += 1
        except Exception as e:
            logging.error(f"Error processing config file {file_path}: {str(e)}")
            self.stats['files_with_errors'] += 1

    def _process_localization_file(self, file_path: str):
        """Process localization files."""
        try:
            relative_path = os.path.relpath(file_path, self.directory)
            locale = self.localization_processor.extract_locale(relative_path)
            localization_node = f"i18n: {os.path.splitext(os.path.basename(relative_path))[0]}"
            if not self.graph.has_node(localization_node):
                self.graph.add_node(
                    localization_node,
                    type="localization",
                    path=relative_path,
                    locale=locale,
                    id=localization_node
                )
                self.stats['total_localizations'] += 1
            # Link localization to file
            file_node = f"File: {relative_path}"
            self.graph.add_edge(file_node, localization_node, relation="CONTAINS")

        except Exception as e:
            logging.error(f"Error processing localization file {file_path}: {str(e)}")
            self.stats['files_with_errors'] += 1

    def _process_documentation_file(self, file_path: str):
        """Process documentation files like README.md and API docs."""
        try:
            relative_path = os.path.relpath(file_path, self.directory)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            doc_info = self.doc_analyzer.analyze_documentation(file_path)
            if doc_info:
                doc_node = f"Documentation: {os.path.relpath(file_path, self.directory)}"
                if not self.graph.has_node(doc_node):
                    self.graph.add_node(
                        doc_node,
                        type="documentation",
                        path=file_path,
                        sections=[section.title for section in doc_info.sections],
                        id=doc_node
                    )
                project_node = "Project: Main"
                if not self.graph.has_node(project_node):
                    self.graph.add_node(project_node, type="project", name="Main Project", id=project_node)
                self.graph.add_edge(project_node, doc_node, relation="HAS_DOCUMENTATION")

        except Exception as e:
            logging.error(f"Error processing documentation file {file_path}: {str(e)}")
            self.stats['files_with_errors'] += 1

    def _process_generic_file(self, file_path: str):
        """Process generic files that don't fall into specific categories."""
        try:
            relative_path = os.path.relpath(file_path, self.directory)
            file_info = self.file_processor.process_file(file_path)
            if file_info:
                file_node = f"File: {relative_path}"
                if not self.graph.has_node(file_node):
                    self.graph.add_node(
                        file_node,
                        type=file_info.type.value,
                        encoding=file_info.encoding or 'UTF-8',
                        fileType=file_info.extension,
                        purpose=file_info.purpose,
                        id=file_node
                    )
        except AttributeError as ae:
            logging.error(f"AttributeError processing generic file {file_path}: {str(ae)}")
            self.stats['files_with_errors'] += 1
        except Exception as e:
            logging.error(f"Error processing generic file {file_path}: {str(e)}")
            self.stats['files_with_errors'] += 1

    def save_graph(self, output_path: str):
        """Save the knowledge graph to a JSON file."""
        try:
            # Convert graph to JSON format with explicit edges keyword to suppress FutureWarning
            data = json_graph.node_link_data(self.graph, edges="links")

            # Prepare metadata
            metadata = {
                "stats": {
                    "total_files": self.total_files,
                    "files_processed": self.files_processed,
                    "files_with_errors": self.stats['files_with_errors'],
                    "total_classes": self.stats['total_classes'],
                    "total_interfaces": self.stats['total_interfaces'],
                    "total_enums": self.stats['total_enums'],
                    "total_methods": self.stats['total_methods'],
                    "total_packages": len(self.stats['total_packages']),
                    "total_imports": self.stats['total_imports'],
                    "total_dependencies": len(self.stats['total_dependencies']),
                    "total_annotations": len(self.stats['total_annotations']),
                    "total_api_endpoints": self.stats['total_api_endpoints'],
                    "total_logging_statements": self.stats['total_logging_statements'],
                    "total_comments": self.stats['total_comments'],
                    "total_configs": self.stats['total_configs'],
                    "total_integrations": self.stats['total_integrations'],
                    "total_localizations": self.stats['total_localizations'],
                    "total_build_scripts": self.stats['total_build_scripts'],
                    "total_version_constraints": self.stats['total_version_constraints']
                },
                "build_info": {
                    "java_version": self.version_analyzer.extract_java_version(),
                    "build_tool": self.build_extractor.get_build_tool(),
                    "main_class": self.code_extractor.get_main_class()
                },
                "documentation": {
                    "readme_path": "README.md",
                    "api_docs": "docs/api.md",
                    "coverage_threshold": self.doc_analyzer.get_coverage_threshold()
                },
                "analysis_timestamp": datetime.now().isoformat(),
                "analyzed_directory": self.directory,
                "packages": list(self.stats['total_packages']),
                "dependencies": list(self.stats['total_dependencies'])
            }

            # Combine data and metadata
            output_data = {
                "graph": {
                    "directed": data['directed'],
                    "multigraph": data['multigraph'],
                    "nodes": data['nodes'],
                    "links": data['links']
                },
                "metadata": metadata
            }

            # Save to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2)

            # Log statistics
            logging.info(f"\nAnalysis Statistics:")
            for key, value in metadata['stats'].items():
                logging.info(f"{key}: {value}")

            logging.info(f"\nKnowledge graph saved to {output_path}")

        except AttributeError as ae:
            logging.error(f"AttributeError saving graph: {str(ae)}")
        except Exception as e:
            logging.error(f"Error saving graph: {str(e)}")

    def generate_example_output_structure(self):
        """Generate an example structure for reference."""
        example_output = {
            "graph": {
                "directed": True,
                "multigraph": False,
                "nodes": [
                    # Nodes will be populated here
                ],
                "links": [
                    # Links will be populated here
                ]
            },
            "metadata": {
                "stats": {
                    "total_files": 0,
                    "files_processed": 0,
                    "files_with_errors": 0,
                    "total_classes": 0,
                    "total_interfaces": 0,
                    "total_enums": 0,
                    "total_methods": 0,
                    "total_packages": 0,
                    "total_imports": 0,
                    "total_dependencies": 0,
                    "total_annotations": 0,
                    "total_api_endpoints": 0,
                    "total_logging_statements": 0,
                    "total_comments": 0,
                    "total_configs": 0,
                    "total_integrations": 0,
                    "total_localizations": 0,
                    "total_build_scripts": 0,
                    "total_version_constraints": 0
                },
                "build_info": {
                    "java_version": "",
                    "build_tool": "",
                    "main_class": ""
                },
                "documentation": {
                    "readme_path": "",
                    "api_docs": "",
                    "coverage_threshold": 0
                },
                "analysis_timestamp": "",
                "analyzed_directory": "",
                "packages": [],
                "dependencies": []
            }
        }
        return example_output


if __name__ == "__main__":
    try:
        print("Java Code Knowledge Graph Generator")
        print("----------------------------------")

        codebase_dir = input("Enter the path to the codebase directory: ").strip()
        if not os.path.exists(codebase_dir):
            raise ValueError(f"Directory does not exist: {codebase_dir}")

        output_file = "java_code_knowledge_graph.json"

        # Create and analyze the codebase
        graph_generator = JavaCodeKnowledgeGraph(directory=codebase_dir)
        graph_generator.analyze_codebase()

        # Save the graph
        graph_generator.save_graph(output_file)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        logging.error(f"Error: {str(e)}")
    finally:
        print("\nDone.")
