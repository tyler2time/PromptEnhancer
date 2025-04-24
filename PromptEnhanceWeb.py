import gradio as gr
import requests
import os
import json
from pathlib import Path
import re

# --- Configuration ---
OLLAMA_ENDPOINT = "http://localhost:11434/v1/chat/completions"
LOCAL_LLM_MODEL = "trollek/qwen2-diffusion-prompter:latest"  # <--- CHANGE THIS to your desired model

# Define paths (Make sure these are correct for your setup)
BASE_FOOCUS_PATH = Path("E:/Fooocus_win64_2-5-0/Fooocus")  # Example Base Path
LORA_PATH = BASE_FOOCUS_PATH / "models/loras"
STYLE_PATH = Path("C:/Fooocus_win64_2-5-0_2/Fooocus/sdxl_styles")
CHECKPOINT_PATH = BASE_FOOCUS_PATH / "models/checkpoints"
LORA_TRIGGER_PATH = Path("loras.json")  # Assumed to be in the script's directory

# --- Style Definitions ---
STYLES = {
    "Visual Detail": "Rewrite the prompt using short, vivid, comma-separated phrases optimized for Stable Diffusion. Focus on clarity, detail, and visual density.",
    "Cinematic": "Transform the prompt into a cinematic composition using stylized, compact phrases suitable for Stable Diffusion.",
    "Fantasy": "Convert the prompt into a vivid, magical scene using concise, descriptive tags and imagery for Stable Diffusion.",
    "Sci-Fi": "Rewrite the prompt into high-tech, futuristic concepts using compact tokens and sci-fi descriptors.",
    "Fantasy Dark": "Rewrite the prompt using dramatic fantasy visuals, with moody lighting, arcane symbolism, and gothic or ancient elements. Keep it concise and rich in dark fantasy imagery.",
    "Sci-Fi Retro": "Enhance the prompt with retrofuturistic and analog sci-fi vibes. Include references to neon, chrome, and vintage tech, formatted as short visual phrases.",
    "Painterly": "Enhance the prompt with textures, brushstroke detail, and classical or digital painting aesthetics. Focus on medium, lighting, and style.",
    "Cyberpunk": "Transform the prompt into a cyberpunk visual style with neon lighting, futuristic decay, high-tech gear, and urban density. Use punchy, descriptive tags.",
    "Surreal Horror": "Rewrite the prompt into a surreal and unsettling horror scene using visual metaphors, uncanny details, and dreamlike symbols.",
    "Cosmic Horror": "Rewrite the prompt using existential and incomprehensible horror themes, with eerie cosmic environments, unknown monsters, and mind-bending visuals.",
    "Techno Horror": "Enhance the prompt with horror imagery involving machines, implants, body distortion, corrupted AIs, and industrial dread.",
    "Alien World": "Rewrite the prompt as a vivid alien landscape, with unfamiliar terrain, alien lifeforms, exotic atmospheres, and sci-fi wonder.",
    "Dystopian Future": "Enhance the prompt using dystopian sci-fi elements like ruined cities, authoritarian tech, bleak environments, and oppressed society themes.",
}


def load_lora_triggers():
    try:
        if LORA_TRIGGER_PATH.exists():
            with open(LORA_TRIGGER_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading LoRA triggers from {LORA_TRIGGER_PATH}: {e}")
    return {}


def get_lora_trigger(lora_name, lora_triggers):
    if lora_name in lora_triggers:
        return lora_triggers[lora_name].get("trigger", "").strip()
    if lora_name:
        cleaned_name = re.sub(r'_v\d+(\.\d+)?$', '', lora_name)
        return cleaned_name.replace("_", " ").replace("-", " ").lower().strip()
    return ""



def load_files_from_path(target_path, extensions):
    files = []
    if not target_path.is_dir():
        print(f"Warning: Path does not exist or is not a directory: {target_path}")
        return []
    try:
        for ext in extensions:
            files.extend(target_path.rglob(f"*{ext}"))
    except Exception as e:
        print(f"Error scanning path {target_path}: {e}")
    if target_path == CHECKPOINT_PATH:
        return sorted(list(set(f.name for f in files)), key=str.lower)
    else:
        return sorted(list(set(f.stem for f in files)), key=str.lower)
def load_loras():
    return load_files_from_path(LORA_PATH, [".safetensors"])


def load_checkpoints():
    return load_files_from_path(CHECKPOINT_PATH, [".safetensors", ".ckpt"])


def load_style_tags():
    tags = []
    if not STYLE_PATH.is_dir():
        print(f"Warning: Style path does not exist or is not a directory: {STYLE_PATH}")
        return []
    for file in STYLE_PATH.glob("*.json"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for entry in data:
                        if isinstance(entry, dict) and "name" in entry and "prompt" in entry:
                            name = entry['name']
                            positive = entry['prompt'].replace("{prompt}", "").strip()
                            negative = entry.get("negative_prompt", "").strip()
                            tags.append(f"{name}::{positive}::{negative}")
                elif isinstance(data, dict):
                    for name, entry_data in data.items():
                        if isinstance(entry_data, dict) and "prompt" in entry_data:
                            positive = entry_data['prompt'].replace("{prompt}", "").strip()
                            negative = entry_data.get("negative_prompt", "").strip()
                            tags.append(f"{name}::{positive}::{negative}")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {file.name}: {e}")
        except Exception as e:
            print(f"Error loading style from {file.name}: {e}")
    return sorted(tags, key=str.lower)


def enhance_prompt(prompt, style, nsfw, token_level, checkpoint, lora, style_tag_entry):
    lora_triggers = load_lora_triggers()
    style_tag_prefix = ""
    negative_prompt = ""
    lora_trigger = get_lora_trigger(lora, lora_triggers) if lora else ""

    if not prompt:
        return "Error: Please enter a basic prompt.", ""

    if style_tag_entry:
        try:
            parts = style_tag_entry.split("::", 2)
            style_tag_prefix = parts[1].strip() if len(parts) > 1 else ""
            negative_prompt = parts[2].strip() if len(parts) > 2 else ""
        except Exception as e:
            print(f"Error parsing style tag entry: {style_tag_entry} - {e}")
            style_tag_prefix = style_tag_entry if "::" not in style_tag_entry else ""

    lora_prefix = f"<lora:{lora}:0.8>, " if lora else ""

    if token_level < 25:
        token_prompt = "Respond using full sentences with rich descriptions. Do not use comma-separated tags."
    elif token_level < 50:
        token_prompt = "Respond using short phrases and some natural language. Blend detail with clarity. Minimal use of tags."
    elif token_level < 75:
        token_prompt = "Compress the description using very short phrases and comma-separated visual descriptors. Avoid full sentences."
    else:
        token_prompt = "Respond ONLY using concise, comma-separated tags and visual descriptors. NO full sentences. Be extremely brief and dense."

    system_prompt = f"You are a prompt enhancer for Stable Diffusion image generation. {STYLES[style]} {token_prompt}"
    if nsfw:
        system_prompt += " Add relevant NSFW, erotic, or suggestive elements as concise tags if appropriate for the base prompt."

    user_prompt_for_api = prompt

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt_for_api}
        ]

        payload = {
            "model": LOCAL_LLM_MODEL,
            "messages": messages,
            "stream": False,
        }

        print(f"--- Sending to Ollama ({LOCAL_LLM_MODEL}) ---")

        response = requests.post(OLLAMA_ENDPOINT, json=payload, timeout=120)
        response.raise_for_status()

        data = response.json()
        enhanced_ai_part = data['choices'][0]['message']['content'].strip()

        final_prompt_parts = []
        if lora_prefix:
            final_prompt_parts.append(lora_prefix.strip())
        if style_tag_prefix:
            final_prompt_parts.append(style_tag_prefix)
        if lora_trigger:
            final_prompt_parts.append(lora_trigger)
        final_prompt_parts.append(enhanced_ai_part)

        final_prompt = ", ".join(filter(None, final_prompt_parts))
        final_prompt = re.sub(r'\s*,\s*', ', ', final_prompt).strip(', ')

        return f"--checkpoint {checkpoint}\n{final_prompt}", negative_prompt

    except requests.exceptions.ConnectionError as e:
        error_msg = f"Connection Error: Could not connect to Ollama at {OLLAMA_ENDPOINT}.\nIs Ollama running? {e}"
        print(error_msg)
        return error_msg, ""
    except requests.exceptions.Timeout:
        error_msg = "Error: Request to Ollama timed out."
        print(error_msg)
        return error_msg, ""
    except requests.exceptions.RequestException as e:
        error_msg = f"Ollama Request Error: {e}"
        try:
            error_msg += f"\nResponse: {e.response.text}"
        except AttributeError:
            pass
        print(error_msg)
        return error_msg, ""
    except (KeyError, IndexError) as e:
        error_msg = f"Error parsing Ollama response: Unexpected format.\n{e}"
        print(error_msg)
        return error_msg, ""
    except Exception as e:
        error_msg = f"An unexpected error occurred: {type(e).__name__}: {e}"
        print(error_msg)
        return error_msg, ""



def save_to_file(positive, negative):
    if not positive:
        return "Error: No enhanced prompt to save."
    try:
        with open("enhanced_prompts.txt", "a", encoding="utf-8") as f:
            f.write("Positive Prompt:\n" + positive + "\n")
            f.write("Negative Prompt:\n" + negative + "\n\n")
        return "Prompt saved to enhanced_prompts.txt"
    except Exception as e:
        return f"Failed to save:\n{e}"


def refresh_loras():
    global loras, lora_triggers  # Declare global variables
    lora_triggers = load_lora_triggers()
    loras = load_loras()
    return gr.Dropdown.update(choices=[""] + loras)


# --- Gradio UI ---
if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        print("The 'requests' library is not installed.\nPlease install it using: pip install requests")
        exit()

    loras = load_loras()  # Load outside the interface
    checkpoints = load_checkpoints()
    style_tags = load_style_tags()

    with gr.Blocks() as iface:
        gr.Markdown("# Stable Diffusion Prompt Enhancer (Ollama)")

        with gr.Row():
            with gr.Column(scale=2):
                prompt_input = gr.Textbox(label="Basic Prompt", lines=2)
                style_select = gr.Dropdown(choices=list(STYLES.keys()), label="Enhance Style", value="Visual Detail")
                token_slider = gr.Slider(minimum=0, maximum=100, value=75, step=1, label="Conciseness")
                nsfw_checkbox = gr.Checkbox(label="NSFW Mode")
            with gr.Column(scale=2):
                checkpoint_select = gr.Dropdown(choices=[""] + checkpoints, label="Checkpoint")
                lora_select = gr.Dropdown(choices=[""] + [""] + loras, label="LoRA", allow_custom_value=True)
                style_tag_select = gr.Dropdown(choices=[""] + style_tags, label="Style Tag", allow_custom_value=True)

        enhance_button = gr.Button("✨ Enhance Prompt ✨")

        with gr.Row():
            positive_output = gr.Textbox(label="Enhanced Prompt", lines=4)
            negative_output = gr.Textbox(label="Negative Prompt", lines=2)

        save_button = gr.Button("Save to File")
        save_status = gr.Textbox(label="Save Status", visible=False)  # Hidden textbox for status

        enhance_button.click(
            enhance_prompt,
            inputs=[prompt_input, style_select, nsfw_checkbox, token_slider, checkpoint_select, lora_select, style_tag_select],
            outputs=[positive_output, negative_output]
        )

        save_button.click(
            save_to_file,
            inputs=[positive_output, negative_output],
            outputs=[save_status]
        )

        lora_select.change(  # Changed from .click() to .change()
            refresh_loras,
            outputs=[lora_select]
        )

    iface.launch()

    print("Gradio interface launched. Visit the URL in your browser to use the Prompt Enhancer.")
    print("Press Ctrl+C to stop the server.")