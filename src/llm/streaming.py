# # streaming.py
# """
# Handle streaming responses for the chat interface
# """
# import logging
# import threading
# import queue
# import time
# from flask import Response

# logger = logging.getLogger(__name__)

# class StreamingResponse:
#     """Handle streaming responses for the chat interface"""
    
#     def __init__(self, generator, prompt):
#         self.generator = generator
#         self.prompt = prompt
#         self.response_queue = queue.Queue()
#         self.thread = None
        
#     def start_generation(self):
#         """Start generating the response in a separate thread"""
#         self.thread = threading.Thread(target=self._generate)
#         self.thread.daemon = True
#         self.thread.start()
        
#     def _generate(self):
#         """Generate the response and put tokens in queue"""
#         try:
#             # Use non-streaming generation as a fallback
#             response = self.generator.generate_response(self.prompt)
            
#             # Add response to queue character by character to simulate streaming
#             for char in response:
#                 self.response_queue.put(char)
#                 time.sleep(0.01)  # Small delay to simulate typing
                
#             # Mark end of generation
#             self.response_queue.put(None)
            
#         except Exception as e:
#             logger.error(f"Error in streaming generation: {e}")
#             self.response_queue.put("I encountered an error while generating the response.")
#             self.response_queue.put(None)
            
#     def get_flask_response(self):
#         """Get a Flask response for streaming"""
#         def generate():
#             while True:
#                 # Get the next token
#                 token = self.response_queue.get()
                
#                 # If None, end of generation
#                 if token is None:
#                     break
                    
#                 # Send the token as an SSE event
#                 yield f"data: {token}\n\n"
                
#             # Send end event
#             yield "data: [END]\n\n"
            
#         return Response(generate(), mimetype="text/event-stream")


# src/llm/streaming.py
"""
Handle streaming responses for the chat interface
"""
import logging
import threading
import queue
import time
from flask import Response

logger = logging.getLogger(__name__)

class StreamingResponse:
    """Handle streaming responses for the chat interface"""
    
    def __init__(self, generator, prompt):
        self.generator = generator
        self.prompt = prompt
        self.response_queue = queue.Queue()
        self.thread = None
        
    def start_generation(self):
        """Start generating the response in a separate thread"""
        self.thread = threading.Thread(target=self._generate)
        self.thread.daemon = True
        self.thread.start()
        
    def _generate(self):
        """Generate the response and put tokens in queue"""
        try:
            # Use non-streaming generation as a fallback
            response = self.generator.generate_response(self.prompt)
            
            # Add response to queue character by character to simulate streaming
            for char in response:
                self.response_queue.put(char)
                time.sleep(0.01)  # Small delay to simulate typing
                
            # Mark end of generation
            self.response_queue.put(None)
            
        except Exception as e:
            logger.error(f"Error in streaming generation: {e}")
            error_msg = "I encountered an error while generating the response."
            for char in error_msg:
                self.response_queue.put(char)
            self.response_queue.put(None)
            
    def get_flask_response(self):
        """Get a Flask response for streaming"""
        def generate():
            while True:
                # Get the next token
                token = self.response_queue.get()
                
                # If None, end of generation
                if token is None:
                    break
                    
                # Send the token as an SSE event
                yield f"data: {token}\n\n"
                
            # Send end event
            yield "data: [END]\n\n"
            
        return Response(generate(), mimetype="text/event-stream")