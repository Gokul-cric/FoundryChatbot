# agents/tools/fishbone_tool.py

from langchain.tools import tool
import subprocess

@tool
def run_fishbone_analysis(foundry: str, defect: str) -> str:
    """Run Fishbone Analytics for the given foundry and defect."""
    try:
        result = subprocess.run(
            ["python", "fishbone_analytics_new.py", foundry, defect],
            capture_output=True, text=True, check=True
        )
        return f"Analysis complete. Charts at results/{foundry}//temp"
    except subprocess.CalledProcessError as e:
        return f"Error running analysis: {e.stderr}"
