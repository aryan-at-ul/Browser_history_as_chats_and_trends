# generator.py
"""
Generate responses using the LLM
"""
import torch
import logging
from datetime import datetime

from src.llm.model_loader import ModelLoader
from src.llm.cache import LLMCache

logger = logging.getLogger(__name__)

class ResponseGenerator:
    """Generate responses using the LLM"""
    
    def __init__(self):
        # Load model if not already loaded
        model_loader = ModelLoader()
        self.model, self.tokenizer, self.generation_config = model_loader.load_model()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.cache = LLMCache()
        
    def generate_response(self, prompt):
        """Generate a response using the LLM"""
        logger.info("Generating response")
        
        # Check cache first
        cached_response = self.cache.get_cached_response(prompt)
        if cached_response:
            logger.info("Using cached response")
            return cached_response
            
        try:
            # Encode the prompt
            input_ids = self.tokenizer.encode(prompt, return_tensors="pt").to(self.device)
            
            # Generate response
            with torch.no_grad():
                outputs = self.model.generate(
                    input_ids,
                    **self.generation_config
                )
                
            # Decode the response, excluding the input prompt
            response = self.tokenizer.decode(outputs[0][input_ids.shape[1]:], skip_special_tokens=True)
            
            # Cache the response
            # Cache the response
            self.cache.cache_response(prompt, response)
            
            logger.info("Generated response")
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I'm sorry, I encountered an error while generating a response. Please try again."
            
    # def generate_streaming_response(self, prompt):
    #     """Generate a streaming response for better UI experience"""
    #     logger.info("Generating streaming response")
        
    #     # Skip cache for streaming responses
    #     try:
    #         # Encode the prompt
    #         input_ids = self.tokenizer.encode(prompt, return_tensors="pt").to(self.device)
            
    #         # Start generation with streaming
    #         tokens = []
            
    #         # Create a copy of generation config without the streaming parameter
    #         gen_config = self.generation_config.copy()
    #         if 'streaming' in gen_config:
    #             del gen_config['streaming']
                
    #         # Stream tokens one by one - use generator directly
    #         for output in self.model.generate(
    #             input_ids,
    #             **gen_config,
    #             streamer=True  # Use streamer parameter instead of streaming
    #         ):
    #             # Get the new token
    #             new_token = output[0, -1].item()
    #             tokens.append(new_token)
                
    #             # Decode just the new token
    #             new_token_text = self.tokenizer.decode([new_token], skip_special_tokens=True)
                
    #             # Yield the new token text for streaming
    #             yield new_token_text
                
    #         # For completeness, cache the full response
    #         full_response = self.tokenizer.decode(tokens, skip_special_tokens=True)
    #         self.cache.cache_response(prompt, full_response)
            
    #     except Exception as e:
    #         logger.error(f"Error generating streaming response: {e}")
    #         yield "I'm sorry, I encountered an error while generating a response. Please try again."

    def generate_streaming_response(self, prompt):
        """Generate a streaming response for better UI experience"""
        logger.info("Generating streaming response")
        
        # For Unsloth, we need to handle streaming differently
        # Instead of streaming directly, we'll just generate the full response
        # and the StreamingResponse class will handle the simulated streaming
        try:
            response = self.generate_response(prompt)
            return response
        except Exception as e:
            logger.error(f"Error generating streaming response: {e}")
            return "I'm sorry, I encountered an error while generating a response. Please try again."
