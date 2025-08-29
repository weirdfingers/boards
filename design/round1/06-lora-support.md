# LoRA Support

## Goals
- Enable creation and reuse of LoRAs (Low-Rank Adapters) for style/character consistency.

## Creation
- Dataset: images + captions; optional trigger token; training params (rank, steps, lr, resolution).
- Job type: `lora.train` writing artifacts to `lora_models` + storage (weights, tokenizer merges, sample outputs).
- Credit accounting: priced per training minute/step.

## Usage
- Include LoRA refs in generation params; providers apply adapters (where supported).
- Hooks expose `useLoras()` to list/apply; backend validates base-model compatibility.
