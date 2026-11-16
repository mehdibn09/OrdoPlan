"""Processus isolé, interrompu par le parent au-delà du budget de lecture."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    import torch
    from PIL import Image
    from transformers import AutoProcessor, AutoModelForImageTextToText
    torch.set_num_threads(2)
    processor = AutoProcessor.from_pretrained(args.model, local_files_only=True, trust_remote_code=False)
    model = AutoModelForImageTextToText.from_pretrained(args.model, local_files_only=True, trust_remote_code=False, torch_dtype=torch.float32)
    image = Image.open(args.image).convert("RGB")
    from src.llm.prompts import load_prompt
    instruction = load_prompt("extract_work_order_v1")["instruction"]
    messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": instruction}]}]
    prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
    inputs = processor(text=prompt, images=[image], return_tensors="pt")
    if inputs["input_ids"].shape[1] > 4096:
        raise ValueError("Contexte supérieur à 4096 tokens")
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=96, do_sample=False, max_time=20)
    text = processor.batch_decode(out[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)[0]
    Path(args.output).write_text(json.dumps({"text": text, "model": str(Path(args.model).name), "source": "local weights"}))


if __name__ == "__main__":
    main()
