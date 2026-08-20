# TripPilot AI — Travel Intent Classification Fine-Tuning Pipeline

This directory contains fine-tuning datasets and instructions to train a specialized, ultra-fast intent classifier using Parameter-Efficient Fine-Tuning (PEFT) / LoRA.

## Target Intent Classes

1. `FLIGHT_SEARCH`
2. `HOTEL_SEARCH`
3. `ACTIVITY_SEARCH`
4. `ITINERARY_PLANNING`
5. `BUDGET_OPTIMIZATION`
6. `BOOKING`
7. `CANCELLATION`
8. `TRAVEL_POLICY`
9. `GENERAL_TRAVEL`

## Dataset Files

- `train.jsonl`: Curated training set formatted as `{"text": "...", "label": "..."}`.
- `validation.jsonl`: Independent evaluation split.

## LoRA / QLoRA Fine-Tuning with Unsloth / Hugging Face Transformers

```python
# Example fine-tuning script using Hugging Face PEFT
from datasets import load_dataset
from transformers import AutoModelForSequenceClassification, AutoTokenizer, Trainer, TrainingArguments
from peft import get_peft_model, LoraConfig, TaskType

# 1. Load base small model (e.g. ModernBERT or DeBERTa-v3-small)
model_name = "answerdotai/ModernBERT-base"
tokenizer = AutoTokenizer.from_pretrained(model_name)
dataset = load_dataset("json", data_files={"train": "training/train.jsonl", "validation": "training/validation.jsonl"})

# 2. Configure LoRA adapter
peft_config = LoraConfig(
    task_type=TaskType.SEQ_CLS,
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["query", "value"]
)

# 3. Train and export lightweight LoRA adapter
```

> **Note**: To ensure zero memory overhead and 100% reliability on lightweight Render deployments, the runtime engine defaults to our high-precision deterministic intent classifier with confidence calibration unless an external fine-tuned model checkpoint is attached.
