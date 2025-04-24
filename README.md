# Prompt Enhancer

Prompt Enhancer is a tool designed to enhance text prompts for use with Stable Diffusion and other AI models. It provides a graphical user interface (GUI) for refining prompts with various styles, LoRA models, and checkpoints.

## Features
- Enhance prompts with predefined styles like "Cinematic," "Fantasy," and "Cyberpunk."
- Support for LoRA models and custom style tags.
- Adjustable conciseness levels for prompt output.
- Save enhanced prompts to a file.

## Requirements
- Python 3.8 or higher
- Required libraries: `openai`, `tkinter`, `pyperclip`, `regex`

## Setup
1. Clone the repository.
2. Install the required libraries using `pip install -r requirements.txt`.
3. Set your OpenAI API key as an environment variable `OPENAI_API_KEY`.

## Usage
Run the application with:
```
python promptenhancer.py
```

## Notes
- Ensure your OpenAI API key is valid and has sufficient quota.
- LoRA and style files should be placed in the appropriate directories as configured in the script.

## File Differences

### ollamapromptenhancer.py
- Focuses on enhancing prompts using the Ollama API.
- Includes advanced configurations for local LLM models and styles.
- Designed for integration with Stable Diffusion workflows.

### promptenhancer.py
- Provides a basic GUI for enhancing prompts.
- Supports predefined styles and LoRA models.
- Simplified for local use without web dependencies.

### PromptEnhanceWeb.py
- Web-based interface for prompt enhancement using Gradio.
- Supports advanced features like NSFW mode, style tags, and checkpoint selection.
- Designed for collaborative or remote usage.