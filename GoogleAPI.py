import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import google.generativeai as genai
import os
import sys
import threading # To run API calls without freezing the GUI

class GeminiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gemini Chat App v0.3 (Persistent Chat)")
        self.root.geometry("700x600") # Initial size

        # --- API Key Configuration ---
        self.api_key_configured = self.configure_api()

        # --- Model Selection ---
        self.available_models = [
            "models/gemini-1.5-pro-latest",   # Default best
            "models/gemini-1.5-flash-latest", # Faster/cheaper
            "models/gemini-1.5-pro",          # Base 1.5 Pro
        ]
        self.model_var = tk.StringVar(value=self.available_models[0]) # Default selection

        # --- Chat State ---
        self.model = None
        self.chat_session = None
        self.current_chat_history_list = [] # Stores history [{'role': ..., 'parts': ...}]

        # --- UI Elements ---
        # Frame for top controls (Model selection)
        controls_frame = ttk.Frame(root, padding="10")
        controls_frame.pack(side=tk.TOP, fill=tk.X)

        model_label = ttk.Label(controls_frame, text="Select Model:")
        model_label.pack(side=tk.LEFT, padx=(0, 5))

        self.model_dropdown = ttk.Combobox(
            controls_frame,
            textvariable=self.model_var,
            values=self.available_models,
            state="readonly",
            width=35
        )
        self.model_dropdown.pack(side=tk.LEFT, padx=(0, 10))
        # --- CHANGE: Bind event handler for model change ---
        self.model_dropdown.bind("<<ComboboxSelected>>", self.on_model_change)

        # Chat History Display
        self.chat_history = scrolledtext.ScrolledText(root, wrap=tk.WORD, state=tk.DISABLED, height=20, relief=tk.SUNKEN, borderwidth=1)
        self.chat_history.pack(padx=10, pady=(0, 5), fill=tk.BOTH, expand=True)
        self.configure_tags()

        # Frame for bottom input
        input_frame = ttk.Frame(root, padding="10")
        input_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.input_entry = tk.Text(input_frame, height=3, relief=tk.SUNKEN, borderwidth=1)
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        self.input_entry.bind("<Return>", self.send_message_event)
        # Consider adding Shift+Return binding for actual newlines if desired later

        self.send_button = ttk.Button(input_frame, text="Send", command=self.send_message_thread)
        self.send_button.pack(side=tk.RIGHT)

        # --- Initial Setup ---
        if self.api_key_configured:
            # --- CHANGE: Initialize chat session on startup ---
            self._initialize_chat_session()
            self.input_entry.focus_set()
        else:
            self.add_to_history("System: WARNING - API Key not configured! Set GOOGLE_API_KEY.\n", style="error")
            self.send_button.config(state=tk.DISABLED)
            self.input_entry.config(state=tk.DISABLED)

    # --- Core Methods ---

    def configure_api(self):
        """Configures the Gemini API key. Returns True on success, False on failure."""
        try:
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set.")
            genai.configure(api_key=api_key)
            print("API Key configured successfully.")
            return True
        except ValueError as e:
            print(f"API Config Error: {e}")
            messagebox.showerror("API Key Error", str(e))
            return False
        except Exception as e:
            print(f"API Config Error: {e}")
            messagebox.showerror("API Configuration Error", f"An unexpected error occurred during API configuration:\n{e}")
            return False

    def _initialize_chat_session(self, model_name=None):
        """Initializes or re-initializes the model and chat session."""
        if not self.api_key_configured:
            self.add_to_history("System: Cannot initialize chat - API Key not configured.\n", "error")
            return

        if model_name is None:
            model_name = self.model_var.get() # Get current selection if not provided

        self.add_to_history(f"System: Initializing chat with {model_name.split('/')[-1]}...\n", "system")
        self.root.update_idletasks() # Show message immediately

        try:
            self.model = genai.GenerativeModel(model_name)
            # --- CHANGE: Clear history and start new chat session ---
            self.current_chat_history_list = []
            self.chat_session = self.model.start_chat(
                history=self.current_chat_history_list # Start with empty history
            )
            # ----------------------------------------------------
            print(f"Chat session initialized successfully with {model_name}")
            self.add_to_history(f"System: Chat session started with {model_name.split('/')[-1]}. History cleared.\n", "system")
            self.enable_input() # Ensure input is enabled

        except Exception as e:
            print(f"Error initializing model/chat: {e}")
            self.add_to_history(f"Error: Failed to initialize model {model_name}. {e}\n", "error")
            # Disable input if initialization fails
            self.input_entry.config(state=tk.DISABLED)
            self.send_button.config(state=tk.DISABLED)

    def on_model_change(self, event=None):
        """Handles the event when a new model is selected."""
        selected_model_name = self.model_var.get()
        # Re-initialize chat with the new model (this will clear history)
        self._initialize_chat_session(selected_model_name)

    def configure_tags(self):
        """Sets up text tags for styling the chat history."""
        self.chat_history.tag_configure("user", foreground="#0000AA") # Dark Blue
        self.chat_history.tag_configure("gemini", foreground="#007700") # Dark Green
        self.chat_history.tag_configure("system", foreground="#555555", font=('TkDefaultFont', 9, 'italic')) # Gray Italic
        self.chat_history.tag_configure("error", foreground="#CC0000", font=('TkDefaultFont', 9, 'bold')) # Dark Red Bold
        self.chat_history.tag_configure("info", foreground="#555555") # Gray normal

    def add_to_history(self, text, style="info"):
        """Adds text to the ScrolledText widget safely from any thread."""
        # Schedule the GUI update to run in the main thread
        self.root.after(0, self._add_to_history_main_thread, text, style)

    def _add_to_history_main_thread(self, text, style):
        """Internal method to update GUI history (runs in main thread)."""
        try:
            scroll_pos = self.chat_history.yview()[1]
            self.chat_history.config(state=tk.NORMAL)
            self.chat_history.insert(tk.END, text, (style,))
            self.chat_history.config(state=tk.DISABLED)
            if scroll_pos > 0.95: # Auto-scroll only if near the bottom
                 self.chat_history.see(tk.END)
        except Exception as e:
            print(f"Error adding to history: {e}")

    def send_message_event(self, event=None):
        """Handles the Enter key press in the input field."""
        self.send_message_thread()
        return "break" # Prevents the default newline insertion

    def send_message_thread(self):
        """Gets input and starts the background thread for the API call."""
        user_input = self.input_entry.get("1.0", tk.END).strip()

        if not user_input or not self.api_key_configured or not self.chat_session:
            if not self.chat_session:
                 self.add_to_history("System: Chat not initialized. Select a model.\n", "error")
            return

        self.add_to_history(f"You: {user_input}\n", style="user")
        # Store user message before clearing input
        self.current_chat_history_list.append({'role':'user', 'parts': [user_input]})

        self.input_entry.delete("1.0", tk.END)
        self.input_entry.config(state=tk.DISABLED)
        self.send_button.config(state=tk.DISABLED)
        self.add_to_history("Gemini: Thinking...\n", style="info")

        # Run the actual API call in a separate thread
        thread = threading.Thread(target=self._send_message_worker, args=(user_input,))
        thread.daemon = True
        thread.start()

    def _send_message_worker(self, user_input):
        """Makes the API call using the persistent chat session (runs in background)."""
        try:
            if not self.chat_session:
                # Should ideally not happen due to check in send_message_thread, but safety check
                raise Exception("Chat session is not initialized.")

            # --- CHANGE: Use persistent chat session ---
            # Pass the raw user input string
            response = self.chat_session.send_message(user_input)
            # --- ------------------------------------ ---

            # Extract response text safely
            response_text = ""
            # The chat session's history is automatically updated internally by send_message
            # We update our list to match for potential saving/reloading later
            if self.chat_session.history and self.chat_session.history[-1].role == 'model':
                 response_part = self.chat_session.history[-1].parts[0]
                 if hasattr(response_part, 'text'):
                      response_text = response_part.text
                 else: # Handle potential non-text parts or blocks if needed
                      response_text = "[Non-text or blocked response part]"
            elif hasattr(response, 'text'): # Fallback if history access differs
                 response_text = response.text
            else:
                 try:
                      # Check for explicit block reasons
                      block_reason = response.prompt_feedback.block_reason
                      response_text = f"[Blocked by API: {block_reason}]"
                 except Exception:
                      response_text = "[Blocked or Empty Response]"


            # --- CHANGE: Update our history list *after* getting response ---
            # Ensure consistency with the chat object's history
            if self.chat_session.history and self.chat_session.history[-1].role == 'model':
                self.current_chat_history_list.append({'role': 'model', 'parts': [response_text]})
            # -------------------------------------------------------------

            # Prepare text for display
            model_short_name = self.model.model_name.split('/')[-1] # Get name from self.model
            display_text = f"Gemini ({model_short_name}): {response_text}\n"

            # Schedule GUI update to add response
            self.add_to_history(display_text, "gemini")

        except Exception as e:
            error_message = f"API Error: {type(e).__name__}: {e}\n"
            print(error_message)
            self.add_to_history(error_message, "error")

            # Clean up our history list if API call failed after adding user message
            if self.current_chat_history_list and self.current_chat_history_list[-1]['role'] == 'user':
                try:
                    self.current_chat_history_list.pop()
                except IndexError:
                    pass # Safety check

        finally:
            # Schedule re-enabling input/button (runs in main thread)
            self.root.after(0, self.enable_input)

    def enable_input(self):
        """Re-enables input widgets (called via root.after)."""
        self.input_entry.config(state=tk.NORMAL)
        self.send_button.config(state=tk.NORMAL)
        # Only focus if the widget still exists (might be destroyed on close)
        if self.input_entry.winfo_exists():
             self.input_entry.focus_set()

# --- Main Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    app = GeminiApp(root)
    root.mainloop()