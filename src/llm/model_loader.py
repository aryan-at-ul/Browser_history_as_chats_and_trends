# model_loader.py
"""
Load and manage the Qwen3-4B model
"""
import os
import logging
import torch
from pathlib import Path
from unsloth import FastLanguageModel

from src.config import (
    LLM_MODEL_NAME, LLM_CACHE_DIR, LLM_MAX_SEQ_LENGTH,
    LORA_R, LORA_ALPHA
)

logger = logging.getLogger(__name__)

class ModelLoader:
    """Load and manage the Qwen3-4B model using Unsloth optimization"""
    
    _instance = None
    _model = None
    _tokenizer = None
    _generation_config = None
    _is_loading = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelLoader, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.model_name = LLM_MODEL_NAME
            self.cache_dir = LLM_CACHE_DIR
            self.max_seq_length = LLM_MAX_SEQ_LENGTH
            self.lora_r = LORA_R
            self.lora_alpha = LORA_ALPHA
            self.initialized = True
        
    def load_model(self):
        """Load the Qwen3-4B model using Unsloth optimization"""
        # If already loaded, return the model
        if self._model is not None and self._tokenizer is not None:
            return self._model, self._tokenizer, self._generation_config
            
        # If currently loading (another thread), wait a bit and check again
        if self._is_loading:
            logger.info("Model is already being loaded by another request, waiting...")
            import time
            time.sleep(5)  # Wait 5 seconds and check again
            return self.load_model()
            
        try:
            # Mark as loading
            self.__class__._is_loading = True
            logger.info(f"Loading model: {self.model_name}")
            
            # Determine device and data type
            if torch.cuda.is_available():
                logger.info("CUDA available, using GPU")
                device = torch.device("cuda")
                dtype = torch.bfloat16
                load_in_4bit = True
            else:
                logger.info("CUDA not available, using CPU")
                device = torch.device("cpu")
                dtype = torch.float32
                load_in_4bit = False
                
            # Load the model with Unsloth optimization
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name=self.model_name,
                max_seq_length=self.max_seq_length,
                cache_dir=self.cache_dir,
                dtype=dtype,
                load_in_4bit=load_in_4bit,
            )
            
            # Configure generation parameters
            generation_config = {
                "max_new_tokens": 512,
                "do_sample": True,
                "temperature": 0.7,
                "top_p": 0.95,
            }
            
            # Apply LoRA optimization
            model = FastLanguageModel.get_peft_model(
                model,
                r=self.lora_r,
                target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
                lora_alpha=self.lora_alpha,
                lora_dropout=0,
                bias="none",
            )
            
            # Store in class variables
            self.__class__._model = model
            self.__class__._tokenizer = tokenizer
            self.__class__._generation_config = generation_config
            
            logger.info(f"Successfully loaded model: {self.model_name}")
            return model, tokenizer, generation_config
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            raise
        finally:
            # Mark as no longer loading
            self.__class__._is_loading = False