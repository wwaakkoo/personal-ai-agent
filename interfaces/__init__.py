"""
Personal AI Agent - æü¶ü¤ó¿üÕ§ü¹
"""

from .cli import CLIInterface

# Web UI n×ìü¹ÛëÀüeŸÅˆš	
class WebInterface:
    def __init__(self, agent):
        self.agent = agent
    
    async def run(self):
        print("Web ¤ó¿üÕ§ü¹o‹z-gY")
        print("CLI ¤ó¿üÕ§ü¹’T)(O`UD: python main.py start")

__all__ = [
    "CLIInterface",
    "WebInterface"
]