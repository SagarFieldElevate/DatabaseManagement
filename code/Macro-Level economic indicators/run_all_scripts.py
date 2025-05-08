import importlib
import os
import sys
from pathlib import Path

# Add code directory to Python path
code_dir = Path(__file__).parent / "code"
sys.path.append(str(code_dir))

# List of script names (without .py extension)
scripts = [
    "Gross Domestic Product",
    "GDP Growth Rate",
    "Inflation Rate (CPI)",
    "Unemployment Rate",
    "Interest Rates (Federal Funds Rate)",
    "Money Supply (M2)",
    "Consumer Confidence Index",
    "Business Confidence Index",
    "Retail Sales",
    "Industrial Production",
    "Capacity Utilization",
    "Purchasing Managers' Index (PMI)",
    "Housing Starts",
    "Building Permits",
    "Trade Balance",
    "Current Account Balance (OECD)",
    "Foreign Direct Investment (FDI) (UNCTAD)",
    "Government Budget Balance (OECD)",
    "Public Debt Levels (IMF)",
    "Exchange Rates (Investing.com)"
]

def run_all_scripts():
    for script_name in scripts:
        try:
            # Convert script name to module name (replace spaces and special chars)
            module_name = script_name.replace(" ", "_").replace("'", "").replace("(", "").replace(")", "").replace(".", "")
            print(f"Running {script_name}...")
            # Import the module
            module = importlib.import_module(module_name)
            # Assuming each script has a function like `get_indicator` or runs its main logic directly
            # Since scripts execute their main logic on import, we just import them
            print(f"✅ Completed {script_name}")
        except Exception as e:
            print(f"❌ Error running {script_name}: {str(e)}")
            continue

if __name__ == "__main__":
    run_all_scripts()
