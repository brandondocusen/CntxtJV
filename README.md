# 📚 CntxtJV: Minify Your Java Codebase Context for LLMs

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](http://makeapullrequest.com)

> 🤯 **75% Token Reduction In Context Window Usage!**

## Why CntxtJV?

-  Boosts precision: Maps relationships and dependencies for clear analysis.
-  Eliminates noise: Focuses LLMs on key code insights.
-  Supports analysis: Reveals architecture for smarter LLM insights.
-  Speeds solutions: Helps LLMs trace workflows and logic faster.
-  Improves recommendations: Gives LLMs detailed metadata for better suggestions.
-  Optimized prompts: Provides structured context for better LLM responses.
-  Streamlines collaboration: Helps LLMs explain and document code easily.


> Supercharge your LLM's understanding of Java codebases. CntxtJV generates comprehensive knowledge graphs that help LLMs navigate and comprehend your code structure with ease.

It's like handing your LLM the cliff notes instead of a novel.

## **Active Enhancement Notice**

- CntxtJV is **actively being enhanced at high velocity with improvements every day**. Thank you for your contributions! 🙌

## ✨ Features

- 🔍 Deep analysis of Java codebases
- 📊 Generates detailed knowledge graphs of:
  - File relationships and dependencies
  - Class hierarchies and methods
  - Method signatures and parameters
  - Package structures
  - Import relationships
  - Maven/Gradle dependencies
  - Annotations and interfaces
- 🎯 Specially designed for LLM context windows
- 📈 Built-in visualization capabilities of your project's knowledge graph
- 🚀 Support for modern Java frameworks and patterns

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/brandondocusen/CntxtJV.git

# Navigate to the directory
cd CntxtJV-main

# Install required packages
pip install python-magic networkx matplotlib

# Run the analyzer
python CntxtJV.py
```

When prompted, enter the path to your Java codebase. The tool will generate a `java_code_knowledge_graph.json` file and offer to visualize the relationships.

## 💡 Example Usage with LLMs

The LLM can now provide detailed insights about your codebase's implementations, understanding the relationships between components, classes, and packages! After generating your knowledge graph, you can upload it as a single file to give LLMs deep context about your codebase. Here's a powerful example prompt:

```Prompt Example
Based on the knowledge graph, explain how the service layer is implemented in this application, including which classes and methods are involved in the process.
```

```Prompt Example
Based on the knowledge graph, map out the core package structure - starting from the main application through to the different modules and their interactions.
```

```Prompt Example
Using the knowledge graph, analyze the dependency injection approach in this application. Which beans exist, what do they manage, and how do they interact with components?
```

```Prompt Example
From the knowledge graph data, break down this application's controller hierarchy, focusing on REST endpoints and their implementation patterns.
```

```Prompt Example
According to the knowledge graph, identify all exception handling patterns in this codebase - where are exceptions caught, how are they processed, and how are they handled?
```

```Prompt Example
Based on the knowledge graph's dependency analysis, outline the key Maven/Gradle dependencies this project relies on and their primary use cases in the application.
```

```Prompt Example
Using the knowledge graph's method analysis, explain how the application handles database interactions and transaction patterns across different services.
```

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

- [ ] Deeper support for additional frameworks (Jakarta EE)
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
