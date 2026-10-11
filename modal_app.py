import os

import modal

gateway_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg")
    .pip_install("fastapi[standard]")
    .add_local_python_source("oolel")
)
tts_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libsndfile1")
    .pip_install("torch", "torchaudio", "librosa>=0.10.2", "transformers==4.46.3", "diffusers==0.29.0",
                 "conformer==0.3.2", "numpy>=2.0.0", "torchcodec", "s3tokenizer", "num2words",
                 "huggingface_hub", "soundfile", "omegaconf", "einops", "resemble-perth", "safetensors",
                 "pyloudnorm")
    .add_local_file("voice.wav", "/app/voice.wav")
)
stt_image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch", "transformers>=4.46", "numpy", "huggingface_hub", "safetensors")
)
app = modal.App("oolel")
cache = modal.Volume.from_name("oolel-hf-cache", create_if_missing=True)


@app.cls(image=tts_image, cpu=8, memory=16384, volumes={"/root/.cache/huggingface": cache},
         scaledown_window=300, max_containers=2, timeout=900)
@modal.concurrent(max_inputs=1)
class Tts:
    @modal.enter()
    def load(self):
        from huggingface_hub import snapshot_download
        from transformers import AutoModel
        self.model = AutoModel.from_pretrained(snapshot_download("soynade-research/Oolel-Voices"),
                                               trust_remote_code=True).to("cpu")
        self.speak.local("Salam.", 7, 0.3, 0.3, 0.5)  # the first call is slow: do it before any request

    @modal.method()
    def speak(self, text, seed, exaggeration, temperature, cfg_weight):
        import io
        import soundfile as sf
        import torch
        if seed is not None:
            torch.manual_seed(seed)
        wav = self.model.generate(text, audio_prompt_path="/app/voice.wav", cfg_weight=cfg_weight,
                                  exaggeration=exaggeration, temperature=temperature)
        buffer = io.BytesIO()
        sf.write(buffer, wav.cpu().squeeze().numpy(), self.model.sr, format="WAV")
        return buffer.getvalue()


@app.cls(image=stt_image, cpu=4, memory=8192, volumes={"/root/.cache/huggingface": cache},
         scaledown_window=300, max_containers=2, timeout=900)
@modal.concurrent(max_inputs=1)
class Stt:
    @modal.enter()
    def load(self):
        import numpy as np
        from transformers import pipeline
        self.asr = pipeline("automatic-speech-recognition", model="soynade-research/Wolof-HuBERT-CTC",
                            chunk_length_s=30, stride_length_s=(5, 5))
        self.asr({"raw": np.zeros(16000, dtype="float32"), "sampling_rate": 16000})  # warm up

    @modal.method()
    def transcribe(self, pcm):
        import numpy as np
        return self.asr({"raw": np.frombuffer(pcm, dtype="float32").copy(), "sampling_rate": 16000})["text"]


@app.function(image=gateway_image, secrets=[modal.Secret.from_name("oolel")], scaledown_window=120)
@modal.asgi_app()
def web():
    from oolel.app import make_app
    return make_app(os.environ["OOLEL_TOKEN"],
                    tts_backend=lambda *args, **kw: Tts().speak.remote(*args, **kw),
                    stt_backend=lambda pcm: Stt().transcribe.remote(pcm))
