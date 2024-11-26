🧠 CntxtJV: Minify Your Java Codebase Context for LLMs
Show Image
Show Image

🤯 75% Token Reduction In Context Window Usage! Supercharge your LLM's understanding of Java codebases. CntxtJV generates comprehensive knowledge graphs that help LLMs navigate and comprehend your code structure with ease.

It's like handing your LLM the cliff notes instead of a novel.
✨ Features

🔍 Deep analysis of Java codebases
📊 Generates detailed knowledge graphs of:

File relationships and dependencies
Class hierarchies and methods
Method signatures and parameters
Package structures
Import relationships
Maven/Gradle dependencies
Annotations and interfaces


🎯 Specially designed for LLM context windows
📈 Built-in visualization capabilities of your project's knowledge graph
🚀 Support for modern Java frameworks and patterns

🚀 Quick Start
bashCopy# Clone the repository
git clone https://github.com/brandondocusen/CntxtJV.git

# Navigate to the directory
cd CntxtJV

# Install required packages
pip install networkx matplotlib

# Run the analyzer
python CntxtJV.py
When prompted, enter the path to your Java codebase. The tool will generate a java_code_knowledge_graph.json file and offer to visualize the relationships.
💡 Example Usage with LLMs
The LLM can now provide detailed insights about your codebase's implementations, understanding the relationships between components, classes, and packages! After generating your knowledge graph, you can upload it as a single file to give LLMs deep context about your codebase. Here's a powerful example prompt:
Prompt Example
Based on the knowledge graph, explain how the service layer is implemented in this application, including which classes and methods are involved in the process.
Copy
```Prompt Example```
Based on the knowledge graph, map out the core package structure - starting from the main application through to the different modules and their interactions.
Prompt Example
Using the knowledge graph, analyze the dependency injection approach in this application. Which beans exist, what do they manage, and how do they interact with components?
Copy
```Prompt Example```
From the knowledge graph data, break down this application's controller hierarchy, focusing on REST endpoints and their implementation patterns.
Prompt Example
According to the knowledge graph, identify all exception handling patterns in this codebase - where are exceptions caught, how are they processed, and how are they handled?
Copy
```Prompt Example```
Based on the knowledge graph's dependency analysis, outline the key Maven/Gradle dependencies this project relies on and their primary use cases in the application.
Prompt Example
Using the knowledge graph's method analysis, explain how the application handles database interactions and transaction patterns across different services.
Copy
## 📊 Output Format

The tool generates two main outputs:
1. A JSON knowledge graph (`java_code_knowledge_graph.json`)
2. Optional visualization using matplotlib

The knowledge graph includes:
- Detailed metadata about your codebase
- Node and edge relationships
- Method parameters and return types
- Class hierarchies
- Import mappings
- Package structures

## 🤝 Contributing

We love contributions! Whether it's:
- 🐛 Bug fixes
- ✨ New features
- 📚 Documentation improvements
- 🎨 Visualization enhancements

Just fork, make your changes, and submit a PR. Check out our [contribution guidelines](CONTRIBUTING.md) for more details.

## 🎯 Future Goals

- [ ] Deeper support for additional frameworks (Spring Boot, Jakarta EE)
- [ ] Enhanced annotation processing
- [ ] Interactive web-based visualizations
- [ ] Custom graph export formats
- [ ] Integration with popular IDEs
- [ ] Support for Kotlin and Scala

## 📝 License

MIT License - feel free to use this in your own projects!

## 🌟 Show Your Support

If you find CntxtJV helpful, give it a star! ⭐️ 

---

Made with ❤️ for the LLM and Java communities
