# /// script
# dependencies = ["trl>=0.12.0", "peft>=0.7.0", "trackio", "datasets", "bitsandbytes"]
# ///

from datasets import load_dataset
from peft import LoraConfig
from trl import SFTTrainer, SFTConfig

# Load Sentinel trade classifier dataset
dataset = load_dataset("mistral-hackaton-2026/sentinel-trade-classifier")
train_ds = dataset["train"]
val_ds = dataset["test"]

print(f"Training examples: {len(train_ds)}")
print(f"Validation examples: {len(val_ds)}")

# LoRA config for efficient fine-tuning
peft_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    task_type="CAUSAL_LM",
)

# SFT training config
training_args = SFTConfig(
    output_dir="sentinel-classifier",
    push_to_hub=True,
    hub_model_id="mistral-hackaton-2026/sentinel-trade-classifier-ministral-8b",
    hub_private_repo=False,

    # Training hyperparameters
    num_train_epochs=3,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    gradient_accumulation_steps=4,
    gradient_checkpointing=True,
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.1,
    weight_decay=0.01,
    max_length=512,

    # Eval
    eval_strategy="steps",
    eval_steps=25,
    save_strategy="steps",
    save_steps=50,
    hub_strategy="every_save",

    # Logging
    logging_steps=5,
    report_to="trackio",
    run_name="sentinel-classifier-v1",

    # Performance
    bf16=True,
    optim="adamw_torch_fused",
    dataloader_num_workers=2,
)

# Initialize trainer
trainer = SFTTrainer(
    model="mistralai/Ministral-8B-Instruct-2410",
    train_dataset=train_ds,
    eval_dataset=val_ds,
    peft_config=peft_config,
    args=training_args,
)

# Train
trainer.train()

# Push final model
trainer.push_to_hub()
print("Training complete! Model pushed to Hub.")
