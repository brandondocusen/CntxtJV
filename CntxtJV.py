# CntxtJV.py - Java codebase analyzer that generates comprehensive knowledge graphs optimized for LLM context windows

import os
import re
import sys
import json
import xml.etree.ElementTree as ET
import networkx as nx
from networkx.readwrite import json_graph
from typing import Dict, List, Optional, Set, Any


class JavaCodeKnowledgeGraph:
    def __init__(self, directory: str):
        """Initialize the knowledge graph generator.

        Args:
            directory: Root directory of the Java codebase.
        """
        self.directory = directory
        self.graph = nx.DiGraph()
        self.class_methods: Dict[str, Set[str]] = {}
        self.method_params: Dict[str, List[Dict[str, Any]]] = {}
        self.method_returns: Dict[str, str] = {}
        self.files_processed = 0
        self.total_files = 0
        self.dirs_processed = 0

        # Track analyzed files to prevent circular dependencies.
        self.analyzed_files = set()

        # Map classes to their defining files.
        self.class_map: Dict[str, str] = {}

        # Directories to ignore during analysis.
        self.ignored_directories = set([
            'target', 'bin', 'build', '.git', '.idea', '.settings', '.gradle',
            '.classpath', '.project', '.metadata', '.vscode', '__pycache__', '.DS_Store',
            'out', 'logs', 'tmp', 'temp', 'test-output', '.mvn', '.svn'
        ])

        # Files to ignore during analysis.
        self.ignored_files = set([
            '.gitignore',
            '.classpath',
            '.project',
            '.DS_Store',
        ])

        # For processing dependencies
        self.dependencies: Set[str] = set()

        # Counters for statistics
        self.total_classes = 0
        self.total_interfaces = 0
        self.total_enums = 0
        self.total_methods = 0
        self.total_packages = set()
        self.total_imports = 0
        self.total_dependencies = set()
        self.total_annotations = set()

    def analyze_codebase(self):
        """Analyze the Java codebase to extract files, imports,
        classes, methods, and their relationships."""
        # First pass to count total files
        print("\nCounting files...")
        for root, dirs, files in os.walk(self.directory):
            # Remove ignored directories from dirs in-place to prevent walking into them
            dirs[:] = [d for d in dirs if d not in self.ignored_directories]

            # Skip if current directory is in ignored directories
            if any(ignored in root.split(os.sep) for ignored in self.ignored_directories):
                continue
            dirs[:] = [d for d in dirs if d not in self.ignored_directories]
            self.total_files += sum(1 for f in files if f not in self.ignored_files and f.endswith(".java"))

        print(f"Found {self.total_files} Java files to process")
        print("\nProcessing files...")

        # Second pass to process files
        for root, dirs, files in os.walk(self.directory):
            # Remove ignored directories from dirs in-place to prevent walking into them
            dirs[:] = [d for d in dirs if d not in self.ignored_directories]

            # Skip if current directory is in ignored directories
            if any(ignored in root.split(os.sep) for ignored in self.ignored_directories):
                continue

            # Display current directory
            rel_path = os.path.relpath(root, self.directory)
            self.dirs_processed += 1
            print(f"\rProcessing directory [{self.dirs_processed}]: {rel_path}", end="")

            for file in files:
                if file in self.ignored_files:
                    continue
                if file.endswith(".java"):
                    file_path = os.path.join(root, file)
                    self._process_file(file_path)
                elif file == "pom.xml":
                    file_path = os.path.join(root, file)
                    self._process_pom_file(file_path)
                elif file == "build.gradle":
                    file_path = os.path.join(root, file)
                    self._process_gradle_file(file_path)

        print(f"\n\nCompleted processing {self.files_processed} files across {self.dirs_processed} directories")

    def _process_file(self, file_path: str):
        """Process a Java file to detect packages, imports, classes, methods, and annotations."""
        if file_path in self.analyzed_files:
            return

        try:
            self.files_processed += 1
            relative_path = os.path.relpath(file_path, self.directory)
            print(f"\rProcessing file [{self.files_processed}/{self.total_files}]: {relative_path}", end="", flush=True)

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            relative_path = os.path.relpath(file_path, self.directory)
            file_node = f"File: {relative_path}"

            # Add to analyzed files set.
            self.analyzed_files.add(file_path)

            # Add file node if it doesn't exist.
            if not self.graph.has_node(file_node):
                self.graph.add_node(file_node, type="file", path=relative_path)

            # Process the file contents.
            package_name = self._process_package(content, file_node)
            self._process_imports(content, file_node)
            self._process_classes(content, file_node, package_name)

        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}", file=sys.stderr)

    def _process_package(self, content: str, file_node: str) -> Optional[str]:
        """Process package declaration in the content."""
        package_pattern = r'package\s+([\w\.]+);'

        match = re.search(package_pattern, content)
        if match:
            package_name = match.group(1)
            package_node = f"Package: {package_name}"

            if not self.graph.has_node(package_node):
                self.graph.add_node(package_node, type="package", name=package_name)
                self.total_packages.add(package_name)

            self.graph.add_edge(package_node, file_node, relation="CONTAINS_FILE")

            return package_name
        return None

    def _process_imports(self, content: str, file_node: str):
        """Process import statements in the content."""
        import_pattern = r'import\s+(static\s+)?([\w\.]+)(\.\*)?;'

        matches = re.finditer(import_pattern, content)
        for match in matches:
            static_import = bool(match.group(1))
            imported_entity = match.group(2)
            is_wildcard = bool(match.group(3))

            import_node = f"Import: {imported_entity}{'.*' if is_wildcard else ''}"
            if not self.graph.has_node(import_node):
                self.graph.add_node(import_node, type="import", name=imported_entity, wildcard=is_wildcard, static=static_import)

            self.graph.add_edge(file_node, import_node, relation="IMPORTS")

            self.total_imports += 1

    def _process_classes(self, content: str, file_node: str, package_name: Optional[str]):
        """Process class, interface, and enum declarations including annotations."""
        class_patterns = [
            # Class declarations with annotations
            r'(?P<annotations>(@[\w\.]+(?:\([^\)]*\))?\s+)*)'
            r'(?P<access_modifier>public\s+|protected\s+|private\s+)?'
            r'(?P<other_modifiers>abstract\s+|final\s+)?'
            r'class\s+(?P<class_name>\w+)\s*'
            r'(?:extends\s+[\w\.]+)?(?:\s+implements\s+[\w\.,\s]+)?\s*\{',

            # Interface declarations with annotations
            r'(?P<annotations>(@[\w\.]+(?:\([^\)]*\))?\s+)*)'
            r'(?P<access_modifier>public\s+|protected\s+|private\s+)?'
            r'(?P<other_modifiers>abstract\s+)?'
            r'interface\s+(?P<class_name>\w+)\s*'
            r'(?:extends\s+[\w\.,\s]+)?\s*\{',

            # Enum declarations with annotations
            r'(?P<annotations>(@[\w\.]+(?:\([^\)]*\))?\s+)*)'
            r'(?P<access_modifier>public\s+|protected\s+|private\s+)?'
            r'enum\s+(?P<class_name>\w+)\s*\{',
        ]

        for pattern in class_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
            for match in matches:
                try:
                    annotations = match.group('annotations') or ''
                    class_type = 'class' if 'class' in match.group(0) else 'interface' if 'interface' in match.group(0) else 'enum'
                    class_name = match.group('class_name')

                    if not class_name:
                        raise ValueError(f"Class name could not be extracted from match: {match.group(0)}")

                    class_node = f"Class: {class_name} ({file_node})"

                    if not self.graph.has_node(class_node):
                        self.graph.add_node(
                            class_node,
                            type=class_type,
                            name=class_name,
                            annotations=self._parse_annotations(annotations)
                        )

                    self.graph.add_edge(file_node, class_node, relation="DEFINES")

                    # Process methods within the class
                    class_body_start = match.end()
                    class_body_end = self._find_matching_brace(content, class_body_start - 1)
                    if class_body_end != -1:
                        class_body = content[class_body_start - 1:class_body_end]
                        self._process_methods(class_body, class_node)
                        self._process_inner_classes(class_body, class_node, package_name)

                    # Update counts
                    if class_type == 'class':
                        self.total_classes += 1
                    elif class_type == 'interface':
                        self.total_interfaces += 1
                    elif class_type == 'enum':
                        self.total_enums += 1

                except Exception as e:
                    print(f"Error processing class in file {file_node}: {str(e)}", file=sys.stderr)
                    print(f"Match: {match.group(0)}", file=sys.stderr)

    def _process_methods(self, content: str, class_node: str):
        """Process method declarations within a class."""
        method_pattern = (
            r'(@[\w\.\(\)\s,"]+\s+)*'        # Annotations
            r'((?:public|protected|private|static|final|abstract|synchronized|native|strictfp)\s+)*'  # Modifiers
            r'([\w\<\>\[\]]+[ \t]+)'          # Return type
            r'(\w+)\s*'                       # Method name
            r'\(([^\)]*)\)'                   # Parameters
            r'(?:\s*throws\s+[\w\.,\s]+)?'    # Throws clause
            r'\s*(\{?|;)'                     # Method body start or abstract method ending with ;
        )

        matches = re.finditer(method_pattern, content, re.MULTILINE)
        for match in matches:
            try:
                annotations = match.group(1) or ''
                modifiers = match.group(2) or ''
                return_type = match.group(3).strip()
                method_name = match.group(4)
                parameters = match.group(5).strip()
                method_body_indicator = match.group(6)

                method_node = f"Method: {method_name} ({class_node})"

                if not self.graph.has_node(method_node):
                    self.graph.add_node(
                        method_node,
                        type="method",
                        name=method_name,
                        return_type=return_type,
                        parameters=self._parse_parameters(parameters),
                        annotations=self._parse_annotations(annotations),
                        modifiers=modifiers.strip().split()
                    )

                self.graph.add_edge(class_node, method_node, relation="HAS_METHOD")

                # **Add return type node and edge**
                return_type_node = f"Type: {return_type}"
                if not self.graph.has_node(return_type_node):
                    self.graph.add_node(return_type_node, type="type", name=return_type)
                self.graph.add_edge(method_node, return_type_node, relation="RETURNS")

                # **Add parameter nodes and edges**
                parameters_list = self._parse_parameters(parameters)
                for param in parameters_list:
                    param_node = f"Parameter: {param['name']} ({method_node})"
                    if not self.graph.has_node(param_node):
                        self.graph.add_node(
                            param_node,
                            type="parameter",
                            name=param['name'],
                            param_type=param['type'],
                            annotations=param['annotations']
                        )
                    self.graph.add_edge(method_node, param_node, relation="HAS_PARAMETER")

                    # Add parameter type node and edge
                    param_type_node = f"Type: {param['type']}"
                    if not self.graph.has_node(param_type_node):
                        self.graph.add_node(param_type_node, type="type", name=param['type'])
                    self.graph.add_edge(param_node, param_type_node, relation="OF_TYPE")

                # **End of inserted code**

                # Track method parameters and returns
                self.method_params[method_node] = parameters_list
                self.method_returns[method_node] = return_type

                # Track class methods
                if class_node not in self.class_methods:
                    self.class_methods[class_node] = set()
                self.class_methods[class_node].add(method_name)

                self.total_methods += 1

                # Process method body if needed (e.g., to find method calls)
                if method_body_indicator == '{':
                    method_body_start = match.end()
                    method_body_end = self._find_matching_brace(content, method_body_start - 1)
                    if method_body_end != -1:
                        method_body = content[method_body_start - 1:method_body_end]
                        # Further processing of method body if needed

            except Exception as e:
                print(f"Error processing method {method_name}: {str(e)}", file=sys.stderr)



    def _process_inner_classes(self, content: str, outer_class_node: str, package_name: Optional[str]):
        """Process inner classes, interfaces, and enums within a class."""
        # Similar to _process_classes but adjusted for inner classes
        class_patterns = [
            # Class declarations with annotations
            r'(?P<annotations>(@[\w\.]+(?:\([^\)]*\))?\s+)*)'
            r'(?P<access_modifier>public\s+|protected\s+|private\s+|static\s+|final\s+)?'
            r'(?P<other_modifiers>abstract\s+|final\s+)?'
            r'class\s+(?P<class_name>\w+)\s*'
            r'(?:extends\s+[\w\.]+)?(?:\s+implements\s+[\w\.,\s]+)?\s*\{',

            # Interface declarations with annotations
            r'(?P<annotations>(@[\w\.]+(?:\([^\)]*\))?\s+)*)'
            r'(?P<access_modifier>public\s+|protected\s+|private\s+|static\s+)?'
            r'(?P<other_modifiers>abstract\s+)?'
            r'interface\s+(?P<class_name>\w+)\s*'
            r'(?:extends\s+[\w\.,\s]+)?\s*\{',

            # Enum declarations with annotations
            r'(?P<annotations>(@[\w\.]+(?:\([^\)]*\))?\s+)*)'
            r'(?P<access_modifier>public\s+|protected\s+|private\s+|static\s+)?'
            r'enum\s+(?P<class_name>\w+)\s*\{',
        ]

        for pattern in class_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
            for match in matches:
                try:
                    annotations = match.group('annotations') or ''
                    class_type = 'class' if 'class' in match.group(0) else 'interface' if 'interface' in match.group(0) else 'enum'
                    class_name = match.group('class_name')
                    class_node = f"Class: {class_name} ({outer_class_node})"

                    if not self.graph.has_node(class_node):
                        self.graph.add_node(
                            class_node,
                            type=class_type,
                            name=class_name,
                            annotations=self._parse_annotations(annotations),
                            is_inner_class=True
                        )

                    self.graph.add_edge(outer_class_node, class_node, relation="HAS_INNER_CLASS")

                    # Process methods within the class
                    class_body_start = match.end()
                    class_body_end = self._find_matching_brace(content, class_body_start - 1)
                    if class_body_end != -1:
                        class_body = content[class_body_start - 1:class_body_end]
                        self._process_methods(class_body, class_node)
                        # Recursively process inner classes
                        self._process_inner_classes(class_body, class_node, package_name)

                    # Update counts
                    if class_type == 'class':
                        self.total_classes += 1
                    elif class_type == 'interface':
                        self.total_interfaces += 1
                    elif class_type == 'enum':
                        self.total_enums += 1

                except Exception as e:
                    print(f"Error processing inner class {class_name}: {str(e)}", file=sys.stderr)

    def _parse_annotations(self, annotations_str: str) -> List[str]:
        """Parse annotations from a string."""
        annotations = re.findall(r'@[\w\.]+', annotations_str)
        for annotation in annotations:
            self.total_annotations.add(annotation)
        return annotations

    def _parse_parameters(self, params_str: str) -> List[Dict[str, Any]]:
        """Parse method parameters including types and add them to the graph."""
        if not params_str:
            return []

        params = []
        param_list = params_str.split(',')

        for param in param_list:
            param = param.strip()
            if not param:
                continue

            # Handle varargs (...)
            param = param.replace('...', '[]')

            # Handle parameter annotations
            annotation_match = re.match(r'(@[\w\.]+\s+)+', param)
            annotations = []
            if annotation_match:
                annotations = re.findall(r'@[\w\.]+', annotation_match.group(0))
                param = param[annotation_match.end():]

            # Split type and name
            type_and_name = param.strip().rsplit(' ', 1)
            if len(type_and_name) == 2:
                param_type, param_name = type_and_name
            else:
                param_type = type_and_name[0]
                param_name = ''

            # **Add parameter type to graph**
            param_type_node = f"Type: {param_type}"
            if not self.graph.has_node(param_type_node):
                self.graph.add_node(param_type_node, type="type", name=param_type)
            # Edge from parameter to its type can be added if parameters are added as nodes

            param_dict = {
                'name': param_name,
                'type': param_type,
                'annotations': annotations
            }
            params.append(param_dict)

        return params

    def _find_matching_brace(self, content: str, start_index: int) -> int:
        """Find the index of the matching closing brace starting from start_index."""
        stack = []
        for index in range(start_index, len(content)):
            if content[index] == '{':
                stack.append('{')
            elif content[index] == '}':
                if stack:
                    stack.pop()
                    if not stack:
                        return index + 1  # Return index after the closing brace
                else:
                    return -1  # Unbalanced braces
        return -1  # No matching brace found

    def _process_pom_file(self, file_path: str):
        """Process Maven pom.xml file to extract dependencies."""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            ns = {'mvn': 'http://maven.apache.org/POM/4.0.0'}

            dependencies = root.find('mvn:dependencies', ns)
            if dependencies is not None:
                for dep in dependencies.findall('mvn:dependency', ns):
                    group_id = dep.find('mvn:groupId', ns).text if dep.find('mvn:groupId', ns) is not None else ''
                    artifact_id = dep.find('mvn:artifactId', ns).text if dep.find('mvn:artifactId', ns) is not None else ''
                    version = dep.find('mvn:version', ns).text if dep.find('mvn:version', ns) is not None else ''
                    scope = dep.find('mvn:scope', ns).text if dep.find('mvn:scope', ns) is not None else 'compile'

                    dependency_name = f"{group_id}:{artifact_id}:{version}"
                    dep_node = f"Dependency: {dependency_name}"
                    if not self.graph.has_node(dep_node):
                        self.graph.add_node(dep_node, type="dependency", group_id=group_id, artifact_id=artifact_id, version=version, scope=scope)
                    self.graph.add_edge(f"File: {os.path.relpath(file_path, self.directory)}", dep_node, relation="HAS_DEPENDENCY")

                    self.dependencies.add(dependency_name)
                    self.total_dependencies.add(dependency_name)

        except Exception as e:
            print(f"Error processing pom.xml {file_path}: {str(e)}", file=sys.stderr)

    def _process_gradle_file(self, file_path: str):
        """Process Gradle build.gradle file to extract dependencies."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            dependency_pattern = r'(implementation|api|compile|runtimeOnly|testImplementation|annotationProcessor)\s+[\'"]([\w\.-]+):([\w\.-]+):([\w\.-]+)[\'"]'
            matches = re.finditer(dependency_pattern, content)
            for match in matches:
                configuration = match.group(1)
                group_id = match.group(2)
                artifact_id = match.group(3)
                version = match.group(4)

                dependency_name = f"{group_id}:{artifact_id}:{version}"
                dep_node = f"Dependency: {dependency_name}"
                if not self.graph.has_node(dep_node):
                    self.graph.add_node(dep_node, type="dependency", group_id=group_id, artifact_id=artifact_id, version=version, configuration=configuration)
                self.graph.add_edge(f"File: {os.path.relpath(file_path, self.directory)}", dep_node, relation="HAS_DEPENDENCY")

                self.dependencies.add(dependency_name)
                self.total_dependencies.add(dependency_name)

        except Exception as e:
            print(f"Error processing build.gradle {file_path}: {str(e)}", file=sys.stderr)

    def save_graph(self, output_path: str):
        """Save the knowledge graph in standard JSON format."""
        data = json_graph.node_link_data(self.graph)
        metadata = {
            "stats": {
                "total_files": self.total_files,
                "total_classes": self.total_classes,
                "total_interfaces": self.total_interfaces,
                "total_enums": self.total_enums,
                "total_methods": self.total_methods,
                "total_types": sum(1 for n in self.graph.nodes.values() if n.get("type") == "type"),
                "total_packages": list(self.total_packages),
                "total_imports": self.total_imports,
                "total_dependencies": list(self.total_dependencies),
                "total_annotations": list(self.total_annotations),
            },
            "method_params": self.method_params,
            "method_returns": self.method_returns,
            "class_methods": {k: list(v) for k, v in self.class_methods.items()},
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"graph": data, "metadata": metadata}, f, indent=2)

    def visualize_graph(self):
        """Visualize the knowledge graph."""
        try:
            import matplotlib.pyplot as plt

            # Create color map for different node types
            color_map = {
                "file": "#ADD8E6",       # Light blue
                "package": "#90EE90",    # Light green
                "class": "#FFE5B4",      # Peach
                "interface": "#FFD700",  # Gold
                "enum": "#FFB6C1",       # Light pink
                "method": "#E6E6FA",     # Lavender
                "import": "#DDA0DD",     # Plum
                "dependency": "#8A2BE2", # Blue Violet
                "type": "#FFA07A",       # Light Salmon
            }


            # Set node colors
            node_colors = [
                color_map.get(self.graph.nodes[node].get("type", "file"), "lightgray")
                for node in self.graph.nodes()
            ]

            # Create figure and axis explicitly
            fig, ax = plt.subplots(figsize=(20, 15))

            # Calculate layout
            pos = nx.spring_layout(self.graph, k=1.5, iterations=50)

            # Draw the graph
            nx.draw(
                self.graph,
                pos,
                ax=ax,
                with_labels=True,
                node_color=node_colors,
                node_size=2000,
                font_size=8,
                font_weight="bold",
                arrows=True,
                edge_color="gray",
                arrowsize=20,
            )

            # Add legend
            legend_elements = [
                plt.Line2D(
                    [0], [0],
                    marker='o',
                    color='w',
                    markerfacecolor=color,
                    label=node_type.capitalize(),
                    markersize=10
                )
                for node_type, color in color_map.items()
            ]

            # Place legend outside the plot
            ax.legend(
                handles=legend_elements,
                loc='center left',
                bbox_to_anchor=(1.05, 0.5),
                title="Node Types"
            )

            # Set title
            ax.set_title("Java Code Knowledge Graph Visualization", pad=20)

            # Adjust layout to accommodate legend
            plt.subplots_adjust(right=0.85)

            # Show plot
            plt.show()

        except ImportError:
            print("Matplotlib is required for visualization. Install it using 'pip install matplotlib'.")

if __name__ == "__main__":
    try:
        # Directory containing the Java codebase.
        print("Java Code Knowledge Graph Generator")
        print("-----------------------------------")
        codebase_dir = input("Enter the path to the codebase directory: ").strip()

        if not os.path.exists(codebase_dir):
            raise ValueError(f"Directory does not exist: {codebase_dir}")

        output_file = "java_code_knowledge_graph.json"

        # Create and analyze the codebase.
        print("\nAnalyzing codebase...")
        ckg = JavaCodeKnowledgeGraph(directory=codebase_dir)
        ckg.analyze_codebase()

        # Save in standard format.
        print("\nSaving graph...")
        ckg.save_graph(output_file)
        print(f"\nCode knowledge graph saved to {output_file}")

        # Display metadata stats
        print("\nCodebase Statistics:")
        print("-------------------")
        stats = {
            "Total Files": ckg.total_files,
            "Total Packages": len(ckg.total_packages),
            "Total Classes": ckg.total_classes,
            "Total Interfaces": ckg.total_interfaces,
            "Total Enums": ckg.total_enums,
            "Total Methods": ckg.total_methods,
            "Total Imports": ckg.total_imports,
            "Total Dependencies": len(ckg.total_dependencies),
            "Total Annotations": len(ckg.total_annotations),
        }

        # Calculate max length for padding
        max_len = max(len(key) for key in stats.keys())

        # Print stats in aligned columns
        for key, value in stats.items():
            print(f"{key:<{max_len + 2}}: {value:,}")

        # Optional visualization.
        while True:
            visualize = input("\nWould you like to visualize the graph? (yes/no): ").strip().lower()
            if visualize in ["yes", "no"]:
                break
            print("Invalid choice. Please enter yes or no.")

        if visualize == "yes":
            print("\nGenerating visualization...")
            ckg.visualize_graph()

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nError: {str(e)}", file=sys.stderr)
    finally:
        print("\nDone.")
