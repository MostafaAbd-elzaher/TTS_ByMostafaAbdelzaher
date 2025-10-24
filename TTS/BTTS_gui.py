import threading
import time
import os
import subprocess
import traceback
from datetime import datetime

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except Exception:
    raise

# Try to import the TTS helper
try:
    from BTTS import create_emotional_tts, available_emotions
except Exception:
    create_emotional_tts = None
    available_emotions = ["neutral", "sad", "happy", "angry", "calm", "excited", "whisper"]


class BTTSGui:
    def __init__(self, root):
        self.root = root
        root.title("BTTS - Child Voice Generator")

        frm = ttk.Frame(root, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")

        # Text input
        ttk.Label(frm, text="Text:").grid(row=0, column=0, sticky="w")
        self.txt = tk.Text(frm, width=60, height=6)
        self.txt.grid(row=1, column=0, columnspan=3, pady=(0, 8))
        self.txt.insert("1.0", "Hello, this is a short child-voice test.")

        # Emotion
        ttk.Label(frm, text="Emotion:").grid(row=2, column=0, sticky="w")
        self.emotion_var = tk.StringVar(value=available_emotions[0])
        self.emotion_cb = ttk.Combobox(
            frm, textvariable=self.emotion_var, values=available_emotions, state="readonly"
        )
        self.emotion_cb.grid(row=2, column=1, sticky="w")

        # Child mode
        self.child_var = tk.BooleanVar(value=True)
        self.child_chk = ttk.Checkbutton(
            frm, text="Child-mode (use child model/post-processing)",
            variable=self.child_var
        )
        self.child_chk.grid(row=3,
                            column=0,
                            columnspan=2,
                            sticky="w",
                            pady=(8, 0)
                            )

        # Custom model (dropdown with optional manual entry)
        ttk.Label(frm, text="Model:").grid(row=4, column=0, sticky="w")
        # sensible defaults
        self.model_choice_var = tk.StringVar()
        model_options = [
            "C3Imaging/child_tts_fastpitch (default child)",
            "tts_models/en/vctk/vits (multi-speaker)",
            "Other (enter manually)",
        ]
        self.model_cb = ttk.Combobox(
            frm, textvariable=self.model_choice_var, values=model_options,
            state="readonly", width=46
        )
        self.model_cb.grid(row=4, column=1, sticky="w")
        self.model_cb.set(model_options[0])

        self.model_custom_var = tk.StringVar()
        self.model_custom_entry = ttk.Entry(
            frm, textvariable=self.model_custom_var, width=36, state="disabled"
        )
        self.model_custom_entry.grid(row=4, column=2, sticky="w")
        self.model_cb.bind(
            "<<ComboboxSelected>>", lambda e: self.on_model_choice_changed())

        # Speaker selection (populated from the selected model)
        ttk.Label(frm, text="Speaker:").grid(row=5, column=0, sticky="w")
        self.speaker_var = tk.StringVar()
        self.speaker_cb = ttk.Combobox(
            frm, textvariable=self.speaker_var, values=[],
            state="disabled", width=46
        )
        self.speaker_cb.grid(row=5, column=1, columnspan=2, sticky="w")

        # Speed
        ttk.Label(frm, text="Global speed multiplier:").grid(row=6, column=0, sticky="w")
        self.speed_var = tk.StringVar(value="1.0")
        self.speed_entry = ttk.Entry(frm, textvariable=self.speed_var, width=8)
        self.speed_entry.grid(row=6, column=1, sticky="w")

        # Pitch slider (semitones)
        ttk.Label(frm, text="Pitch shift (semitones):").grid(row=7, column=0, sticky="w")
        self.pitch_var = tk.DoubleVar(value=0.0)
        self.pitch_slider = ttk.Scale(
            frm, from_=-7.0, to=7.0, orient="horizontal", variable=self.pitch_var
        )
        self.pitch_slider.grid(row=7, column=1, columnspan=2, sticky="we")
        self.pitch_val_lbl = ttk.Label(frm, textvariable=tk.StringVar(value=str(self.pitch_var.get())))
        self.pitch_val_lbl.grid(row=7, column=3, sticky="w")

        # Energy/gain slider
        ttk.Label(frm, text="Energy (gain x):").grid(row=8, column=0, sticky="w")
        self.energy_var = tk.DoubleVar(value=1.0)
        self.energy_slider = ttk.Scale(
            frm, from_=0.2, to=2.0, orient="horizontal", variable=self.energy_var
        )
        self.energy_slider.grid(row=8, column=1, columnspan=2, sticky="we")
        self.energy_val_lbl = ttk.Label(frm, textvariable=tk.StringVar(value=str(self.energy_var.get())))
        self.energy_val_lbl.grid(row=8, column=3, sticky="w")

        # Additional expressive controls: tremolo, reverb, brightness
        ttk.Label(frm, text="Tremolo rate (Hz):").grid(row=12, column=0, sticky="w")
        self.trem_rate_var = tk.DoubleVar(value=5.0)
        self.trem_rate_entry = ttk.Entry(frm, textvariable=self.trem_rate_var, width=8)
        self.trem_rate_entry.grid(row=12, column=1, sticky="w")
        self.trem_rate_val_lbl = ttk.Label(frm, textvariable=tk.StringVar(value=str(self.trem_rate_var.get())))
        self.trem_rate_val_lbl.grid(row=12, column=4, sticky="w")

        ttk.Label(frm, text="Tremolo depth (0-1):").grid(row=12, column=2, sticky="w")
        self.trem_depth_var = tk.DoubleVar(value=0.0)
        self.trem_depth_slider = ttk.Scale(frm, from_=0.0, to=1.0, orient="horizontal", variable=self.trem_depth_var)
        self.trem_depth_slider.grid(row=12, column=3, sticky="we")
        self.trem_depth_val_lbl = ttk.Label(frm, textvariable=tk.StringVar(value=str(self.trem_depth_var.get())))
        self.trem_depth_val_lbl.grid(row=12, column=5, sticky="w")

        ttk.Label(frm, text="Reverb amount (0-1):").grid(row=13, column=0, sticky="w")
        self.reverb_var = tk.DoubleVar(value=0.0)
        self.reverb_slider = ttk.Scale(frm, from_=0.0, to=1.0, orient="horizontal", variable=self.reverb_var)
        self.reverb_slider.grid(row=13, column=1, columnspan=3, sticky="we")
        self.reverb_val_lbl = ttk.Label(frm, textvariable=tk.StringVar(value=str(self.reverb_var.get())))
        self.reverb_val_lbl.grid(row=13, column=4, sticky="w")

        ttk.Label(frm, text="Brightness (-1..1):").grid(row=14, column=0, sticky="w")
        self.brightness_var = tk.DoubleVar(value=0.0)
        self.brightness_slider = ttk.Scale(frm, from_=-1.0, to=1.0, orient="horizontal", variable=self.brightness_var)
        self.brightness_slider.grid(row=14, column=1, columnspan=3, sticky="we")
        self.brightness_val_lbl = ttk.Label(frm, textvariable=tk.StringVar(value=str(self.brightness_var.get())))
        self.brightness_val_lbl.grid(row=14, column=4, sticky="w")

        # Wire up traces so value labels update live
        def _bind_var_display(var, label_var):
            def _on_change(*_):
                try:
                    val = var.get()
                except Exception:
                    val = ''
                label_var.set(str(round(float(val), 3)) if val != '' else '')
            var.trace_add('write', _on_change)
            _on_change()

        # create StringVars for labels and bind
        self._pitch_label_var = tk.StringVar()
        self.pitch_val_lbl.config(textvariable=self._pitch_label_var)
        _bind_var_display(self.pitch_var, self._pitch_label_var)

        self._energy_label_var = tk.StringVar()
        self.energy_val_lbl.config(textvariable=self._energy_label_var)
        _bind_var_display(self.energy_var, self._energy_label_var)

        self._trem_rate_label_var = tk.StringVar()
        self.trem_rate_val_lbl.config(textvariable=self._trem_rate_label_var)
        _bind_var_display(self.trem_rate_var, self._trem_rate_label_var)

        self._trem_depth_label_var = tk.StringVar()
        self.trem_depth_val_lbl.config(textvariable=self._trem_depth_label_var)
        _bind_var_display(self.trem_depth_var, self._trem_depth_label_var)

        self._reverb_label_var = tk.StringVar()
        self.reverb_val_lbl.config(textvariable=self._reverb_label_var)
        _bind_var_display(self.reverb_var, self._reverb_label_var)

        self._brightness_label_var = tk.StringVar()
        self.brightness_val_lbl.config(textvariable=self._brightness_label_var)
        _bind_var_display(self.brightness_var, self._brightness_label_var)

        # Output path
        ttk.Label(frm, text="Output file name:").grid(row=9, column=0, sticky="w")
        self.out_var = tk.StringVar(value=f"child_output_{int(time.time())}.wav")
        self.out_entry = ttk.Entry(frm, textvariable=self.out_var, width=48)
        self.out_entry.grid(row=9, column=1, columnspan=2, sticky="w")

        # Generate button and status
        self.generate_btn = ttk.Button(frm, text="Generate", command=self.on_generate)
        self.generate_btn.grid(row=10, column=0, pady=(12, 0))

        self.open_btn = ttk.Button(frm, text="Open Output", command=self.open_output)
        self.open_btn.grid(row=10, column=1, pady=(12, 0))

        self.status_var = tk.StringVar(value="Ready")
        self.status_lbl = ttk.Label(frm, textvariable=self.status_var)
        self.status_lbl.grid(row=11, column=0, columnspan=3, sticky="w", pady=(8, 0))

        # make grid expand
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

    def set_status(self, text):
        self.status_var.set(text)
        self.root.update_idletasks()

    def on_model_choice_changed(self):
        sel = self.model_choice_var.get().strip()
        if sel.startswith("Other"):
            # enable manual entry and disable speaker list
            self.model_custom_entry.config(state="normal")
            self.speaker_cb.config(state="disabled")
            self.speaker_cb['values'] = []
            self.speaker_var.set("")
            return
        else:
            self.model_custom_entry.config(state="disabled")

        # derive model name string
        if sel.startswith("C3Imaging/"):
            model_name = "C3Imaging/child_tts_fastpitch"
        else:
            model_name = "tts_models/en/vctk/vits"

        # populate speakers in background
        th = threading.Thread(target=self._populate_speakers_thread, args=(model_name,), daemon=True)
        th.start()

    def _populate_speakers_thread(self, model_name):
        # attempt to initialize the TTS probe and read speakers
        self.set_status(f"Probing model for speakers: {model_name}")
        try:
            from TTS.api import TTS
            tts = None
            try:
                tts = TTS(model_name=model_name)
            except Exception:
                # try fallback without raising
                tts = None
            if tts and getattr(tts, 'speakers', None):
                spk = [s.strip() for s in tts.speakers]
                # update UI in main thread
                self.root.after(0, lambda: self._set_speakers_ui(spk))
                self.set_status(f"Loaded {len(spk)} speakers from model")
            else:
                self.root.after(0, lambda: self._set_speakers_ui([]))
                self.set_status("No speakers available for this model")
        except Exception as e:
            self.root.after(0, lambda: self._set_speakers_ui([]))
            self.set_status(f"Speaker probe failed: {e}")

    def _set_speakers_ui(self, speakers):
        if speakers:
            self.speaker_cb['values'] = speakers
            self.speaker_cb.config(state="readonly")
            # default select first
            self.speaker_var.set(speakers[0])
        else:
            self.speaker_cb['values'] = []
            self.speaker_cb.config(state="disabled")
            self.speaker_var.set("")

    def open_output(self):
        path = self.out_var.get()
        if not os.path.exists(path):
            messagebox.showerror("File not found", f"Output file does not exist: {path}")
            return
        try:
            if os.name == 'posix':
                subprocess.Popen(["xdg-open", path])
            else:
                os.startfile(path)
        except Exception as e:
            messagebox.showerror("Open failed", str(e))

    def on_generate(self):
        if create_emotional_tts is None:
            messagebox.showerror("BTTS import error", "Could not import create_emotional_tts from BTTS.py. Make sure BTTS.py is in the same folder and imports without prompts.")
            return
        text = self.txt.get("1.0", "end").strip()
        if not text:
            messagebox.showerror("No text", "Please enter text to synthesize.")
            return
        emotion = self.emotion_var.get()
        child_mode = bool(self.child_var.get())
        # resolve selected model
        sel = self.model_choice_var.get().strip()
        if sel.startswith("C3Imaging/"):
            model_name = "C3Imaging/child_tts_fastpitch"
        elif sel.startswith("tts_models/en/vctk/vits"):
            model_name = "tts_models/en/vctk/vits"
        elif sel.startswith("Other"):
            model_name = self.model_custom_var.get().strip() or None
        else:
            # fallback
            model_name = None
        try:
            global_speed = float(self.speed_var.get())
        except Exception:
            global_speed = 1.0

        out = self.out_var.get().strip() or f"child_output_{int(time.time())}.wav"

        # run in background thread
        try:
            pitch = float(self.pitch_var.get())
        except Exception:
            pitch = 0.0
        try:
            energy = float(self.energy_var.get())
        except Exception:
            energy = 1.0
        trem_rate = float(self.trem_rate_var.get()) if hasattr(self, 'trem_rate_var') else 5.0
        trem_depth = float(self.trem_depth_var.get()) if hasattr(self, 'trem_depth_var') else 0.0
        reverb_amt = float(self.reverb_var.get()) if hasattr(self, 'reverb_var') else 0.0
        brightness = float(self.brightness_var.get()) if hasattr(self, 'brightness_var') else 0.0

        th = threading.Thread(
            target=self._generate_thread,
            args=(
                text,
                emotion,
                out,
                model_name,
                child_mode,
                global_speed,
                pitch,
                energy,
                trem_rate,
                trem_depth,
                reverb_amt,
                brightness,
            ),
            daemon=True,
        )
        th.start()

    def _generate_thread(self, text, emotion, out, model_name, child_mode, global_speed, pitch_shift, energy, trem_rate, trem_depth, reverb_amt, brightness):
        try:
            self.generate_btn.config(state="disabled")
            self.set_status("Starting generation...")
            # choose model_name fallback
            chosen_model = model_name or ("C3Imaging/child_tts_fastpitch" if child_mode else "tts_models/en/vctk/vits")
            self.set_status(f"Initializing model: {chosen_model}")
            # call the create_emotional_tts function
            try:
                create_emotional_tts(
                    text,
                    emotion,
                    out,
                    speaker=None,
                    tts_instance=None,
                    speaker_gender=None,
                    global_speed=global_speed,
                    model_name=chosen_model,
                    child_mode=child_mode,
                    pitch_shift=pitch_shift,
                    energy=energy,
                    tremolo_rate=trem_rate,
                    tremolo_depth=trem_depth,
                    reverb_amount=reverb_amt,
                    brightness=brightness,
                )
                self.set_status(f"Done. Saved to {out}")
            except Exception as e:
                # fallback: if child-mode and chosen_model failed, try vctk/vits + post-processing
                tb = traceback.format_exc()
                self.set_status("Generation failed: falling back to vctk approximation...")
                try:
                    # fallback to vctk model
                    create_emotional_tts(
                        text,
                        emotion,
                        out,
                        speaker=None,
                        tts_instance=None,
                        speaker_gender=None,
                        global_speed=global_speed,
                        model_name="tts_models/en/vctk/vits",
                        child_mode=True,
                        pitch_shift=pitch_shift,
                        energy=energy,
                    )
                    self.set_status(f"Done with fallback. Saved to {out}")
                except Exception as e2:
                    self.set_status("All generation attempts failed")
                    messagebox.showerror("Generation failed", f"Errors:\n{tb}\n{traceback.format_exc()}")
        finally:
            self.generate_btn.config(state="normal")


if __name__ == "__main__":
    root = tk.Tk()
    app = BTTSGui(root)
    root.mainloop()
