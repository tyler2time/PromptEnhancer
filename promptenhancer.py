import tkinter as tk
from tkinter import ttk, messagebox
import openai
import pyperclip
import os
import json
from pathlib import Path
import regex as re

# Set your OpenAI API key here directly or via environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

# If the environment variable is not set, uncomment the next line and add your key
# BUT DO NOT COMMIT YOUR KEY TO VERSION CONTROL
# if not openai.api_key: openai.api_key = "sk-REPLACE_THIS_WITH_YOUR_KEY"

# Define paths (Consider making these configurable)
BASE_FOOCUS_PATH = Path("E:/Fooocus_win64_2-5-0/Fooocus") # Example Base Path
LORA_PATH = BASE_FOOCUS_PATH / "models/loras"
# Using a different path for styles as per original code
STYLE_PATH = Path("C:/Fooocus_win64_2-5-0_2/Fooocus/sdxl_styles")
CHECKPOINT_PATH = BASE_FOOCUS_PATH / "models/checkpoints"
LORA_TRIGGER_PATH = Path("loras.json") # Assumed to be in the script's directory or a config location

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
    "Dystopian Future": "Enhance the prompt using dystopian sci-fi elements like ruined cities, authoritarian tech, bleak environments, and oppressed society themes."
}

# --- Main Application Class ---
class PromptEnhancerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Prompt Enhancer v2.1 (Grid Layout)")
        self.root.minsize(700, 650) # Increased min height slightly for status bar

        # --- Internal state ---
        self.status_clear_job = None # To store the 'after' job ID for status clear

        # --- Pre-load data ---
        self.lora_triggers = self.load_lora_triggers()
        self.checkpoints = self.load_checkpoints()
        self.loras = self.load_loras()
        self.style_tags = self.load_style_tags()

        # --- Configure Root Grid Weights (for resizing) ---
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        # Allow row 2 (output frame) to expand vertically
        self.root.grid_rowconfigure(2, weight=1)
        # Row 3 is Enhance button (no weight)
        # Row 4 is Status Bar (no weight)

        # --- Create Frames for Layout ---
        input_style_frame = ttk.LabelFrame(root, text="Input & Style Settings", padding=(10, 5))
        input_style_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")
        input_style_frame.grid_columnconfigure(1, weight=1)

        model_frame = ttk.LabelFrame(root, text="Model & File Settings", padding=(10, 5))
        model_frame.grid(row=0, column=1, padx=10, pady=(10, 5), sticky="nsew")
        model_frame.grid_columnconfigure(1, weight=1)

        output_frame = ttk.LabelFrame(root, text="Output", padding=(10, 5))
        # Place output frame in row 2
        output_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=(5, 5), sticky="nsew")
        output_frame.grid_columnconfigure(1, weight=1)
        output_frame.grid_rowconfigure(0, weight=1)
        output_frame.grid_rowconfigure(1, weight=1)

        # --- Populate Input & Style Frame ---
        # (Widgets placed inside input_style_frame as before)
        prompt_label = ttk.Label(input_style_frame, text="Basic Prompt:")
        prompt_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 2))
        self.input_text = tk.Text(input_style_frame, height=5, width=40)
        self.input_text.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        style_label = ttk.Label(input_style_frame, text="Enhance Style:")
        style_label.grid(row=2, column=0, sticky="w", padx=(0, 5))
        self.style_var = tk.StringVar(value="Visual Detail")
        self.style_menu = ttk.Combobox(input_style_frame, textvariable=self.style_var, values=list(STYLES.keys()), state="readonly", width=25)
        self.style_menu.grid(row=2, column=1, sticky="ew", pady=(0, 5))
        token_label = ttk.Label(input_style_frame, text="Conciseness:")
        token_label.grid(row=3, column=0, sticky="w", padx=(0, 5))
        self.token_scale = ttk.Scale(input_style_frame, from_=0, to=100, orient="horizontal")
        self.token_scale.set(75)
        self.token_scale.grid(row=3, column=1, sticky="ew", pady=(0, 5))
        self.nsfw_var = tk.BooleanVar()
        nsfw_check = ttk.Checkbutton(input_style_frame, text="NSFW Mode", variable=self.nsfw_var)
        nsfw_check.grid(row=4, column=0, columnspan=2, sticky="w", pady=(5, 0))

        # --- Populate Model & File Frame ---
        # (Widgets placed inside model_frame as before)
        cp_label = ttk.Label(model_frame, text="Checkpoint:")
        cp_label.grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.checkpoint_var = tk.StringVar()
        self.checkpoint_menu = ttk.Combobox(model_frame, textvariable=self.checkpoint_var, values=self.checkpoints, state="readonly", width=25)
        self.checkpoint_menu.grid(row=0, column=1, sticky="ew", pady=(0, 5))
        if self.checkpoints: self.checkpoint_menu.current(0)
        lora_label = ttk.Label(model_frame, text="LoRA:")
        lora_label.grid(row=1, column=0, sticky="w", padx=(0, 5))
        self.lora_var = tk.StringVar()
        lora_options = [""] + self.loras
        self.lora_menu = ttk.Combobox(model_frame, textvariable=self.lora_var, values=lora_options, state="readonly", width=25)
        self.lora_menu.grid(row=1, column=1, sticky="ew", pady=(0, 5))
        self.lora_menu.bind("<Button-1>", lambda e: self.refresh_loras())
        style_tag_label = ttk.Label(model_frame, text="Style Tag:")
        style_tag_label.grid(row=2, column=0, sticky="w", padx=(0, 5))
        self.style_tag_var = tk.StringVar()
        style_tag_options = [""] + self.style_tags
        self.style_tag_menu = ttk.Combobox(model_frame, textvariable=self.style_tag_var, values=style_tag_options, state="readonly", width=25)
        self.style_tag_menu.grid(row=2, column=1, sticky="ew", pady=(0, 5))

        # --- Enhance Button ---
        # Place enhance button in row 1
        enhance_button = ttk.Button(root, text="✨ Enhance Prompt ✨", command=self.enhance_prompt)
        enhance_button.grid(row=1, column=0, columnspan=2, pady=10)

        # --- Populate Output Frame ---
        # (Widgets placed inside output_frame as before)
        positive_label = ttk.Label(output_frame, text="Enhanced Prompt:")
        positive_label.grid(row=0, column=0, sticky="nw", padx=(0, 5), pady=(0,2)) # Align label top-left
        self.output_text = tk.Text(output_frame, height=6, width=60)
        self.output_text.grid(row=0, column=1, sticky="nsew", pady=(0, 5))
        negative_label = ttk.Label(output_frame, text="Negative Prompt:")
        negative_label.grid(row=1, column=0, sticky="nw", padx=(0, 5), pady=(0,2)) # Align label top-left
        self.negative_text = tk.Text(output_frame, height=4, width=60)
        self.negative_text.grid(row=1, column=1, sticky="nsew", pady=(0, 10))
        save_button = ttk.Button(output_frame, text="Save to File", command=self.save_to_file)
        save_button.grid(row=2, column=1, sticky="e", pady=(5, 0))

        # --- Status Bar ---
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor='w', padding=(5, 2))
        # Place status bar in row 3
        self.status_bar.grid(row=3, column=0, columnspan=2, sticky='ew', padx=5, pady=(5, 5))

        # --- Final Check for API Key ---
        if not openai.api_key:
            self.show_status("Warning: OpenAI API key not found.", error=True)
            enhance_button.configure(state=tk.DISABLED)

    # --- Helper Method for Status Bar ---
    def show_status(self, message, duration=4000, error=False):
        """Updates the status bar message and optionally clears it after a duration."""
        # Cancel any previous clearing job
        if self.status_clear_job:
            self.root.after_cancel(self.status_clear_job)
            self.status_clear_job = None

        self.status_var.set(message)
        if error:
            # You might need to define styles or use specific themes for colors
            # For simplicity, we'll just prepend "Error: " or "Warning: "
            self.status_var.set(f"Error: {message}") # Or use foreground colors if desired
            # self.status_bar.config(foreground='red')
        else:
            # self.status_bar.config(foreground='black') # Reset color
            pass # Keep default color

        if duration:
            self.status_clear_job = self.root.after(duration, self.clear_status)

    def clear_status(self):
        """Clears the status bar message."""
        self.status_var.set("")
        # self.status_bar.config(foreground='black') # Ensure color is reset
        self.status_clear_job = None


    # --- Backend Methods (Mostly Unchanged, except enhance_prompt) ---

    def load_lora_triggers(self):
        try:
            if LORA_TRIGGER_PATH.exists():
                with open(LORA_TRIGGER_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading LoRA triggers from {LORA_TRIGGER_PATH}: {e}")
            self.show_status(f"Could not load LoRA triggers: {e}", error=True)
        return {}

    def get_lora_trigger(self, lora_name):
        if lora_name in self.lora_triggers:
            return self.lora_triggers[lora_name].get("trigger", "").strip()
        if lora_name:
            cleaned_name = re.sub(r'_v\d+(\.\d+)?$', '', lora_name)
            return cleaned_name.replace("_", " ").replace("-", " ").lower().strip()
        return ""

    def load_files_from_path(self, target_path, extensions):
        files = []
        if not target_path.is_dir():
            print(f"Warning: Path does not exist or is not a directory: {target_path}")
            self.show_status(f"Path not found: {target_path}", error=True)
            return []
        try:
            for ext in extensions:
                files.extend(target_path.rglob(f"*{ext}"))
        except Exception as e:
            print(f"Error scanning path {target_path}: {e}")
            self.show_status(f"Error scanning path: {target_path}", error=True)
        if target_path == CHECKPOINT_PATH:
             return sorted(list(set(f.name for f in files)), key=str.lower)
        else:
             return sorted(list(set(f.stem for f in files)), key=str.lower)

    def load_loras(self):
        return self.load_files_from_path(LORA_PATH, [".safetensors"])

    def refresh_loras(self):
        self.show_status("Refreshing LoRAs...")
        self.lora_triggers = self.load_lora_triggers()
        self.loras = self.load_loras()
        lora_options = [""] + self.loras
        self.lora_menu["values"] = lora_options
        self.show_status(f"Found {len(self.loras)} LoRAs.", duration=3000)

    def load_checkpoints(self):
        return self.load_files_from_path(CHECKPOINT_PATH, [".safetensors", ".ckpt"])

    def load_style_tags(self):
        tags = []
        if not STYLE_PATH.is_dir():
             print(f"Warning: Style path does not exist or is not a directory: {STYLE_PATH}")
             self.show_status(f"Style path not found: {STYLE_PATH}", error=True)
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
                self.show_status(f"JSON Error in {file.name}", error=True)
            except Exception as e:
                print(f"Error loading style from {file.name}: {e}")
                self.show_status(f"Error loading style {file.name}", error=True)
        return sorted(tags, key=str.lower)

    def enhance_prompt(self):
        if not openai.api_key:
             messagebox.showerror("API Key Error", "OpenAI API key is missing. Cannot enhance.")
             self.show_status("API Key Error", error=True)
             return

        prompt = self.input_text.get("1.0", tk.END).strip()
        if not prompt:
            messagebox.showerror("Input Error", "Please enter a basic prompt.")
            self.show_status("Input Error: Prompt missing", error=True)
            return

        # Show busy status
        self.show_status("Enhancing prompt...", duration=None) # None = indefinite until next update
        self.root.update_idletasks() # Force UI update to show status immediately

        selected_style_name = self.style_var.get()
        nsfw = self.nsfw_var.get()
        lora = self.lora_var.get()
        style_tag_entry = self.style_tag_var.get()
        checkpoint = self.checkpoint_var.get()
        token_level = self.token_scale.get()

        style_tag_prefix = ""
        negative_prompt = ""
        lora_trigger = self.get_lora_trigger(lora) if lora else ""

        if style_tag_entry:
            try:
                parts = style_tag_entry.split("::", 2)
                style_tag_prefix = parts[1].strip() if len(parts) > 1 else ""
                negative_prompt = parts[2].strip() if len(parts) > 2 else ""
            except Exception as e:
                print(f"Error parsing style tag entry: {style_tag_entry} - {e}")
                style_tag_prefix = style_tag_entry if "::" not in style_tag_entry else ""

        lora_prefix = f"<lora:{lora}:0.8>, " if lora else ""

        if token_level < 25: token_prompt = "Respond using full sentences with rich descriptions. Do not use comma-separated tags."
        elif token_level < 50: token_prompt = "Respond using short phrases and some natural language. Blend detail with clarity. Minimal use of tags."
        elif token_level < 75: token_prompt = "Compress the description using very short phrases and comma-separated visual descriptors. Avoid full sentences."
        else: token_prompt = "Respond ONLY using concise, comma-separated tags and visual descriptors. NO full sentences. Be extremely brief and dense."

        system_prompt = f"You are a prompt enhancer for Stable Diffusion. {STYLES[selected_style_name]} {token_prompt}"
        if nsfw: system_prompt += " Add relevant NSFW, erotic, or suggestive elements as concise tags if appropriate for the base prompt."

        user_prompt_for_api = prompt
        if lora_trigger: user_prompt_for_api += f" (incorporate elements related to: {lora_trigger})"

        print("--- Sending to OpenAI ---")
        print(f"System Prompt: {system_prompt}")
        print(f"User Prompt: {user_prompt_for_api}")
        print("-------------------------")

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt_for_api}
                ]
            )
            enhanced_ai_part = response['choices'][0]['message']['content'].strip()

            final_prompt_parts = []
            if lora_prefix: final_prompt_parts.append(lora_prefix.strip())
            if style_tag_prefix: final_prompt_parts.append(style_tag_prefix)
            if lora_trigger: final_prompt_parts.append(lora_trigger)
            final_prompt_parts.append(enhanced_ai_part)

            final_prompt = ", ".join(filter(None, final_prompt_parts))
            final_prompt = re.sub(r'(?<!<lora:[^>]+):', '', final_prompt) # Remove colons unless inside lora tag
            final_prompt = re.sub(r'\s*,\s*', ', ', final_prompt).strip(', ') # Standardize comma spacing

            self.output_text.delete("1.0", tk.END)
            self.output_text.insert(tk.END, f"--checkpoint {checkpoint}\n{final_prompt}")
            self.negative_text.delete("1.0", tk.END)
            self.negative_text.insert(tk.END, negative_prompt)

            pyperclip.copy(final_prompt)
            # *** THIS IS THE CHANGED LINE ***
            self.show_status("Prompt copied to clipboard!", duration=3000) # Show status instead of messagebox

        except openai.error.AuthenticationError as e:
             messagebox.showerror("API Error", f"Authentication Failed. Check your OpenAI API key.\n{e}")
             self.show_status("API Authentication Error", error=True)
        except openai.error.RateLimitError as e:
             messagebox.showerror("API Error", f"Rate limit exceeded. Please wait and try again.\n{e}")
             self.show_status("API Rate Limit Error", error=True)
        except Exception as e:
            error_type = type(e).__name__
            print(f"Unhandled error during enhancement: {error_type}: {e}") # Log the full error
            messagebox.showerror("API Error", f"Failed to enhance prompt:\n{error_type}: {e}")
            self.show_status(f"Error during enhancement: {error_type}", error=True)


    def save_to_file(self):
        positive = self.output_text.get("1.0", tk.END).strip()
        negative = self.negative_text.get("1.0", tk.END).strip()
        if not positive:
            # Use status bar for this minor error too
            self.show_status("Error: No enhanced prompt to save.", error=True)
            return

        output_filename = "enhanced_prompts.txt"
        try:
            with open(output_filename, "a", encoding="utf-8") as f:
                f.write("--- Prompt ---\n")
                f.write("Positive Prompt:\n" + positive + "\n\n")
                f.write("Negative Prompt:\n" + negative + "\n")
                f.write("--------------\n\n")
            # Confirm save via status bar
            self.show_status(f"Prompt saved to {output_filename}", duration=3000)
        except Exception as e:
            # Show error in status bar and messagebox for file saving failure
            self.show_status(f"Save Error: {e}", error=True)
            messagebox.showerror("Save Error", f"Failed to save to {output_filename}:\n{e}")


# --- Main Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    app = PromptEnhancerGUI(root)
    root.mainloop()