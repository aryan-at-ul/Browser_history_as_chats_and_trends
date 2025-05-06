# # prompt_builder.py
# """
# Build prompts for the LLM
# """
# import logging

# from src.config import SYSTEM_PROMPT

# logger = logging.getLogger(__name__)

# class PromptBuilder:
#     """Build prompts for the LLM"""
    
#     def __init__(self):
#         self.system_prompt = SYSTEM_PROMPT
        
#     def build_chat_prompt(self, user_query, context_chunks):
#         """Build a prompt for the chat interaction with context from RAG"""
#         logger.info(f"Building chat prompt with {len(context_chunks)} context chunks")
        
#         # Format context chunks as a string
#         context_parts = []
#         for i, chunk in enumerate(context_chunks):
#             source_info = f"[{i+1}] Source: {chunk['url']}"
#             if 'domain' in chunk:
#                 source_info += f" (Domain: {chunk['domain']})"
            
#             context_parts.append(f"{source_info}\nContent: {chunk['chunk_text']}")
            
#         context = "\n\n".join(context_parts)
        
#         # Build the full prompt following Qwen3 format
#         prompt = f"""<|im_start|>system
# {self.system_prompt}

# I have access to the following information from your browsing history:

# {context}
# <|im_end|>

# <|im_start|>user
# {user_query}
# <|im_end|>

# <|im_start|>assistant
# """
        
#         return prompt
        
#     def build_summary_prompt(self, history_data, period="recent"):
#         """Build a prompt for generating browsing history summaries"""
#         logger.info(f"Building summary prompt for {period} history")
        
#         # Format history data as a string
#         history_items = []
#         for item in history_data:
#             history_items.append(
#                 f"- URL: {item['url']}\n"
#                 f"  Title: {item['title'] or 'Untitled'}\n"
#                 f"  Visited: {item['last_visit_time']}"
#             )
            
#         history_text = "\n".join(history_items)
        
#         prompt = f"""<|im_start|>system
# {self.system_prompt}

# I need you to analyze and summarize the following {period} browsing history:

# {history_text}
# <|im_end|>

# <|im_start|>user
# Please give me a summary of my recent browsing activity. What topics have I been focusing on? Are there any patterns or trends you notice?
# <|im_end|>

# <|im_start|>assistant
# """
        
#         return prompt
        
#     def build_domain_analysis_prompt(self, domain, history_data):
#         """Build a prompt for analyzing browsing activity on a specific domain"""
#         logger.info(f"Building domain analysis prompt for {domain}")
        
#         # Filter for the specified domain
#         domain_items = [item for item in history_data if item.get('domain') == domain]
        
#         # Format domain data
#         domain_items_text = []
#         for item in domain_items:
#             domain_items_text.append(
#                 f"- URL: {item['url']}\n"
#                 f"  Title: {item['title'] or 'Untitled'}\n"
#                 f"  Visited: {item['last_visit_time']}"
#             )
            
#         history_text = "\n".join(domain_items_text)
        
#         prompt = f"""<|im_start|>system
# {self.system_prompt}

# I need you to analyze my browsing activity on {domain}:

# {history_text}
# <|im_end|>

# <|im_start|>user
# What have I been looking at on {domain}? What topics or patterns do you notice in my browsing on this site?
# <|im_end|>

# <|im_start|>assistant
# """
        
#         return prompt


# """
# Build prompts for the LLM with enhanced context handling
# """
# import logging
# from datetime import datetime

# from src.config import SYSTEM_PROMPT

# logger = logging.getLogger(__name__)

# class PromptBuilder:
#     """Build prompts for the LLM with improved context handling"""
    
#     def __init__(self):
#         self.system_prompt = SYSTEM_PROMPT
        
#     def build_chat_prompt(self, user_query, context_chunks):
#         """Build a prompt for the chat interaction with context from RAG"""
#         logger.info(f"Building chat prompt with {len(context_chunks)} context chunks")
        
#         # Extract time frame information if present
#         time_frame = self._extract_time_frame(user_query)
#         time_description = self._get_time_description(time_frame)
        
#         # Determine if this is an activity summary type query
#         is_activity_query = self._is_activity_query(user_query)
        
#         # Format context chunks as a string with enhanced metadata
#         context_parts = []
#         for i, chunk in enumerate(context_chunks):
#             # Build source info with enhanced metadata
#             source_info = f"[{i+1}] Source: {chunk.get('title', 'Untitled')} - {chunk.get('url', 'No URL')}"
            
#             # Add domain info if available
#             if 'domain' in chunk:
#                 source_info += f" (Domain: {chunk['domain']})"
            
#             # Add time context if available
#             if 'last_visit_time' in chunk and chunk['last_visit_time']:
#                 try:
#                     visit_time = datetime.fromisoformat(chunk['last_visit_time'])
#                     days_ago = (datetime.now() - visit_time).days
                    
#                     if days_ago == 0:
#                         source_info += " (Visited today)"
#                     elif days_ago == 1:
#                         source_info += " (Visited yesterday)"
#                     else:
#                         source_info += f" (Visited {days_ago} days ago)"
#                 except (ValueError, TypeError):
#                     pass
            
#             # Add visit frequency if available
#             if 'visit_count' in chunk and chunk['visit_count'] > 1:
#                 source_info += f" (Visited {chunk['visit_count']} times)"
            
#             # Add relevance notes if available
#             if 'relevance_notes' in chunk and chunk['relevance_notes']:
#                 notes = '; '.join(chunk['relevance_notes'])
#                 source_info += f"\nRelevance: {notes}"
            
#             # Add the chunk content
#             content = chunk.get('chunk_text', 'No content available')
#             context_parts.append(f"{source_info}\nContent: {content}")
        
#         # Join all context parts
#         context = "\n\n".join(context_parts)
        
#         # Build additional instructions based on query type
#         additional_instructions = ""
#         if is_activity_query:
#             additional_instructions = f"""
# You are analyzing the user's browsing history {time_description}. 
# Focus on identifying topics, patterns, and interests from their browsing activity.
# Organize your response by topics or themes, and mention specific websites or content 
# they've shown interest in. Be specific about time periods when relevant.
# """
        
#         # Build the full prompt following Qwen3 format
#         prompt = f"""<|im_start|>system
# {self.system_prompt}

# {additional_instructions}
# I have access to the following information from your browsing history:

# {context}
# <|im_end|>

# <|im_start|>user
# {user_query}
# <|im_end|>

# <|im_start|>assistant
# """
        
#         return prompt
        
#     def build_summary_prompt(self, history_data, period="recent"):
#         """Build a prompt for generating browsing history summaries"""
#         logger.info(f"Building summary prompt for {period} history")
        
#         # Group history data by domain for better analysis
#         domains = {}
#         for item in history_data:
#             domain = item.get('domain', 'unknown')
#             if domain not in domains:
#                 domains[domain] = []
#             domains[domain].append(item)
        
#         # Format domains and their entries
#         domain_sections = []
#         for domain, items in domains.items():
#             if not items:
#                 continue
                
#             domain_items = []
#             for item in items:
#                 domain_items.append(
#                     f"  - Title: {item.get('title', 'Untitled')}\n"
#                     f"    URL: {item.get('url', 'No URL')}\n"
#                     f"    Visited: {item.get('last_visit_time', 'Unknown')}"
#                 )
            
#             domain_section = f"Domain: {domain} ({len(items)} pages)\n" + "\n".join(domain_items)
#             domain_sections.append(domain_section)
            
#         history_text = "\n\n".join(domain_sections)
        
#         # Build specific instructions based on the period
#         period_instructions = ""
#         if period == "today":
#             period_instructions = "Focus on today's browsing patterns and interests."
#         elif period == "this week":
#             period_instructions = "Analyze the past week's browsing activity to identify trends and interests."
#         elif period == "this month":
#             period_instructions = "Provide a monthly overview highlighting major themes and changes in browsing habits."
        
#         prompt = f"""<|im_start|>system
# {self.system_prompt}

# I need you to analyze and summarize the following {period} browsing history.
# {period_instructions}
# Organize your analysis by topics or themes rather than by websites.
# Focus on identifying patterns, interests, and trends.

# Here is the browsing history data organized by domain:

# {history_text}
# <|im_end|>

# <|im_start|>user
# Please give me a summary of my {period} browsing activity. What topics have I been focusing on? Are there any patterns or trends you notice?
# <|im_end|>

# <|im_start|>assistant
# """
        
#         return prompt
        
#     def build_domain_analysis_prompt(self, domain, history_data):
#         """Build a prompt for analyzing browsing activity on a specific domain"""
#         logger.info(f"Building domain analysis prompt for {domain}")
        
#         # Filter for the specified domain
#         domain_items = [item for item in history_data if item.get('domain') == domain]
        
#         # Find the time span
#         dates = []
#         for item in domain_items:
#             if 'last_visit_time' in item and item['last_visit_time']:
#                 try:
#                     dates.append(datetime.fromisoformat(item['last_visit_time']))
#                 except (ValueError, TypeError):
#                     pass
                    
#         time_span = ""
#         if len(dates) >= 2:
#             earliest = min(dates)
#             latest = max(dates)
#             days_span = (latest - earliest).days
            
#             if days_span == 0:
#                 time_span = "today"
#             elif days_span <= 7:
#                 time_span = f"in the past {days_span} days"
#             elif days_span <= 30:
#                 time_span = f"in the past month"
#             else:
#                 time_span = f"over the past {days_span} days"
        
#         # Format domain data
#         domain_items_text = []
#         for item in domain_items:
#             domain_items_text.append(
#                 f"- Title: {item.get('title', 'Untitled')}\n"
#                 f"  URL: {item.get('url', 'No URL')}\n"
#                 f"  Visited: {item.get('last_visit_time', 'Unknown')}"
#             )
            
#         history_text = "\n".join(domain_items_text)
        
#         prompt = f"""<|im_start|>system
# {self.system_prompt}

# I need you to analyze my browsing activity on {domain} {time_span}.
# Focus on identifying specific topics, content types, and interests I've shown on this domain.
# Be specific about patterns you notice in the content I've viewed.

# Here is my browsing history on {domain}:

# {history_text}
# <|im_end|>

# <|im_start|>user
# What have I been looking at on {domain}? What topics or patterns do you notice in my browsing on this site?
# <|im_end|>

# <|im_start|>assistant
# """
        
#         return prompt
        
#     def build_comparative_prompt(self, user_query, context_chunks, time_period=None):
#         """Build a prompt for comparative analysis of browsing behavior over time"""
#         logger.info(f"Building comparative prompt with {len(context_chunks)} context chunks")
        
#         # Group content by time periods
#         time_groups = self._group_by_time_periods(context_chunks)
        
#         # Format each time period's content
#         time_period_sections = []
#         for period, chunks in time_groups.items():
#             if not chunks:
#                 continue
                
#             section_items = []
#             for chunk in chunks:
#                 section_items.append(
#                     f"- {chunk.get('title', 'Untitled')} ({chunk.get('domain', 'Unknown domain')})"
#                 )
                
#             section = f"Period: {period} ({len(chunks)} pages)\n" + "\n".join(section_items)
#             time_period_sections.append(section)
            
#         context = "\n\n".join(time_period_sections)
        
#         prompt = f"""<|im_start|>system
# {self.system_prompt}

# I need you to compare my browsing behavior across different time periods.
# Identify changes in interests, topics, and browsing patterns over time.
# Focus on meaningful shifts rather than listing all visited sites.

# Here is my browsing history grouped by time period:

# {context}
# <|im_end|>

# <|im_start|>user
# {user_query}
# <|im_end|>

# <|im_start|>assistant
# """
        
#         return prompt
    
#     def _extract_time_frame(self, query):
#         """Extract time frame from query (in days)"""
#         query_lower = query.lower()
        
#         # Check for time references
#         time_refs = {
#             'today': 1,
#             'yesterday': 2,
#             'this week': 7,
#             'past week': 7,
#             'this month': 30,
#             'recent': 14,
#             'recently': 14,
#             'last week': 14,
#             'past few days': 5
#         }
        
#         for ref, days in time_refs.items():
#             if ref in query_lower:
#                 return days
                
#         return None
    
#     def _get_time_description(self, days):
#         """Convert days to a natural language description"""
#         if not days:
#             return "recently"
            
#         if days == 1:
#             return "today"
#         elif days == 2:
#             return "yesterday and today"
#         elif days <= 7:
#             return "this week"
#         elif days <= 14:
#             return "in the past two weeks"
#         elif days <= 30:
#             return "this month"
#         else:
#             return f"in the past {days} days"
    
#     def _is_activity_query(self, query):
#         """Check if this is an activity summary query"""
#         query_lower = query.lower()
        
#         activity_terms = [
#             'what have i', 'been doing', 'looked at', 'searched for',
#             'browsing history', 'activity', 'visited', 'browsed',
#             'been reading', 'been researching', 'been interested in',
#             'topics', 'summary', 'overview'
#         ]
        
#         return any(term in query_lower for term in activity_terms)
    
#     def _group_by_time_periods(self, chunks):
#         """Group chunks by time periods for comparative analysis"""
#         today = []
#         this_week = []
#         this_month = []
#         earlier = []
        
#         now = datetime.now()
        
#         for chunk in chunks:
#             if 'last_visit_time' not in chunk or not chunk['last_visit_time']:
#                 earlier.append(chunk)
#                 continue
                
#             try:
#                 visit_time = datetime.fromisoformat(chunk['last_visit_time'])
#                 days_ago = (now - visit_time).days
                
#                 if days_ago == 0:
#                     today.append(chunk)
#                 elif days_ago <= 7:
#                     this_week.append(chunk)
#                 elif days_ago <= 30:
#                     this_month.append(chunk)
#                 else:
#                     earlier.append(chunk)
#             except (ValueError, TypeError):
#                 earlier.append(chunk)
        
#         return {
#             'Today': today,
#             'This Week (excluding today)': this_week,
#             'This Month (excluding this week)': this_month,
#             'Earlier': earlier
#         }





# src/llm/prompt_builder.py
"""
Build prompts for the LLM
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

from src.config import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Build prompts for the LLM"""

    # ────────────────────────────────────────────────────────────────────────
    def __init__(self) -> None:
        self.system_prompt = SYSTEM_PROMPT

    # ────────────────────────────────────────────────────────────────────────
    # Helpers
    # ────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _clean_title(raw: str | None) -> str:
        """
        Remove noise from scraped <title> strings so the LLM sees clean text.
        • Strips stray logger lines / code snippets
        • Masks Cloudflare “verify you are human” pages
        • Drops “- Google Search”, “- Bing” suffixes
        """
        if not raw:
            return "Untitled"

        title = raw.strip()

        # logger.*("…") artefacts
        title = re.sub(r'logger\.\w+\([\'"].*?[\'"]\)', '', title, flags=re.I)

        # Cloudflare human‑verification pages
        if re.search(r"verify (you are|you're) human", title, flags=re.I):
            return "[cloudflare challenge]"

        # Search‑engine suffixes
        title = re.sub(r"\s*[-|–]\s*(Google|Google Search|Bing|Yahoo!?)\s*Search?.*$", "", title, flags=re.I)

        # Collapse whitespace
        title = re.sub(r"\s+", " ", title).strip()

        return title or "Untitled"

    # ────────────────────────────────────────────────────────────────────────
    # Prompt builders
    # ────────────────────────────────────────────────────────────────────────
    def build_chat_prompt(self, user_query: str, context_chunks: list[dict]) -> str:
        """Prompt for RAG chat."""
        logger.info("Building chat prompt with %d context chunks", len(context_chunks))

        parts = []
        for i, chunk in enumerate(context_chunks):
            src = f"[{i + 1}] Source: {chunk['url']}"
            if "domain" in chunk:
                src += f" (Domain: {chunk['domain']})"
            parts.append(f"{src}\nContent: {chunk['chunk_text']}")

        context = "\n\n".join(parts)

        prompt = (
            "<|im_start|>system\n"
            f"{self.system_prompt}\n\n"
            "I have access to the following information from your browsing history:\n\n"
            f"{context}\n"
            "<|im_end|>\n\n"
            "<|im_start|>user\n"
            f"{user_query}\n"
            "<|im_end|>\n\n"
            "<|im_start|>assistant\n"
        )
        return prompt

    def build_summary_prompt(self, history_data: list[dict], period: str = "recent") -> str:
        """Prompt for summarising browsing history (clean titles!)."""
        logger.info("Building summary prompt for %s history", period)

        lines = []
        for item in history_data:
            title = self._clean_title(item.get("title"))
            visited = item.get("last_visit_time", "unknown")
            lines.append(f"- Visited: {visited}\n  Title: {title}")

        history_text = "\n".join(lines[:200])  # cap length

        prompt = (
            "<|im_start|>system\n"
            f"{self.system_prompt}\n\n"
            f"I need you to analyse and summarise the following {period} browsing history:\n\n"
            f"{history_text}\n"
            "<|im_end|>\n\n"
            "<|im_start|>user\n"
            "Please give me a concise summary of my recent browsing activity. "
            "What topics have I been focusing on? Any patterns or trends?\n"
            "<|im_end|>\n\n"
            "<|im_start|>assistant\n"
        )
        return prompt

    def build_domain_analysis_prompt(self, domain: str, history_data: list[dict]) -> str:
        """Prompt for analysing activity on a single domain (clean titles!)."""
        logger.info("Building domain analysis prompt for %s", domain)

        domain_items_text = []
        for item in history_data:
            if item.get("domain") != domain:
                continue
            title = self._clean_title(item.get("title"))
            visited = item.get("last_visit_time", "unknown")
            domain_items_text.append(f"- Visited: {visited}\n  Title: {title}")

        history_text = "\n".join(domain_items_text)

        prompt = (
            "<|im_start|>system\n"
            f"{self.system_prompt}\n\n"
            f"I need you to analyse my browsing activity on {domain}:\n\n"
            f"{history_text}\n"
            "<|im_end|>\n\n"
            "<|im_start|>user\n"
            f"What have I been looking at on {domain}? Any topics or patterns stand out?\n"
            "<|im_end|>\n\n"
            "<|im_start|>assistant\n"
        )
        return prompt
