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


    # Add these methods to your prompt_builder.py file

    def build_period_summary_prompt(self, start_date, end_date, history_data):
        """Build a prompt for generating a summary of browsing activity for a time period"""
        total_items = len(history_data)
        unique_domains = len(set([item.get('domain', '') for item in history_data]))
        
        prompt = f"""Analyze the user's browsing history from {start_date} to {end_date}. 
    There are {total_items} browsing history entries across {unique_domains} unique domains.

    Create a concise summary (3-4 paragraphs) that highlights:
    1. Major themes and topics in their browsing
    2. Most frequently visited domains and what this indicates about their interests
    3. Any patterns in browsing behavior (time of day, specific topics, etc.)
    4. Interesting insights about what they might have been researching or working on

    Focus on providing valuable observations that help the user understand their digital activities during this time period.

    Browse History Data:
    """
        
        # Add a sample of history data (limit to ~50 entries if very large)
        sample_size = min(50, len(history_data))
        sample = history_data[:sample_size]
        
        for item in sample:
            prompt += f"- {item.get('last_visit_time', '')}: {item.get('title', '')} ({item.get('domain', '')})\n"
        
        # Add instruction to keep response concise
        prompt += "\nProvide your analysis in a concise, informative format. Focus on meaningful patterns and insights."
        
        return prompt

    def build_period_analysis_prompt(self, start_date, end_date, history_data):
        """Build a prompt for generating a detailed analysis of browsing activity for a time period"""
        total_items = len(history_data)
        
        # Calculate domain frequencies
        domain_counts = {}
        for item in history_data:
            domain = item.get('domain', '')
            if domain:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        # Sort domains by frequency
        sorted_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)
        top_domains = sorted_domains[:10]
        
        domain_summary = "\n".join([f"- {domain}: {count} visits" for domain, count in top_domains])
        
        prompt = f"""Generate a detailed analysis of the user's browsing history from {start_date} to {end_date}.
    This analysis will help them understand their online activity during this period.

    BROWSING OVERVIEW:
    - Time period: {start_date} to {end_date}
    - Total pages visited: {total_items}
    - Top domains visited:
    {domain_summary}

    Please provide a comprehensive analysis that includes:

    1. MAJOR THEMES AND TOPICS:
    Identify the main topics and themes in their browsing history. What were they researching or interested in?

    2. BROWSING PATTERNS:
    Analyze patterns in their browsing behavior, such as:
    - Types of content consumed (articles, videos, social media, etc.)
    - Time-based patterns (specific days or times they were most active)
    - Topical trends and how interests evolved during this period

    3. DOMAIN ANALYSIS:
    Provide insights about their most visited domains and what this indicates about their interests or work.

    4. KEY INSIGHTS:
    Offer 3-5 specific insights that might be valuable or surprising to the user.

    5. SUMMARY:
    Conclude with a brief paragraph that captures the essence of their online activity during this period.

    Base your analysis on this browsing history data:
    """
        
        # Add history data (limit to ~100 entries if very large)
        sample_size = min(100, len(history_data))
        sample = history_data[:sample_size]
        
        for item in sample:
            prompt += f"- {item.get('last_visit_time', '')}: {item.get('title', '')} ({item.get('domain', '')})\n"
        
        prompt += "\nProvide your detailed analysis in a well-structured, easily readable format."
        
        return prompt

    def build_date_chat_prompt(self, date, query, history_data):
        """Build a prompt for chatting about browsing activity on a specific date"""
        prompt = f"""You are an AI assistant helping the user understand their browsing history on {date}. 
    The user has asked: "{query}"

    Please respond to their question based on their browsing activity from this date. 
    If the question isn't directly related to their browsing history, try to connect it to what they were doing online that day.

    Here is their browsing history from {date}:
    """
        
        # Add the history data
        for item in history_data:
            prompt += f"- {item.get('last_visit_time', '')}: {item.get('title', '')} ({item.get('domain', '')})\n"
        
        prompt += "\nRespond to their question in a helpful, conversational way, focusing on their browsing data from this date."
        
        return prompt