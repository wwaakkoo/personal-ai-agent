"""
Personal AI Agent - �������է��
"""

from .cli import CLIInterface

# Web UI n��������e�ň�	
class WebInterface:
    def __init__(self, agent):
        self.agent = agent
    
    async def run(self):
        print("Web ���է��o�z-gY")
        print("CLI ���է���T)(O`UD: python main.py start")

__all__ = [
    "CLIInterface",
    "WebInterface"
]