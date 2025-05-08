import importlib
import os
import sys
import time
from pathlib import Path
import traceback

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
    success_count = 0
    failed_scripts = []
    
    for script_name in scripts:
        start_time = time.time()
        print(f"\n[START] Running {script_name}...")
        try:
            # Convert script name to module name (replace spaces and special chars)
            module_name = script_name.replace(" ", "_").replace("'", "").replace("(", "").replace(")", "").replace(".", "")
            # Import the module
            module = importlib.import_module(module_name)
            # Scripts execute their main logic on import
            elapsed_time = time.time() - start_time
            print(f"[SUCCESS] Completed {script_name} in {elapsed_time:.2f} seconds")
            success_count += 1
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_message = f"[ERROR] Failed {script_name} in {elapsed_time:.2f} seconds: {str(e)}"
            stack_trace = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            print(error_message)
            print(f"[STACK TRACE]\n{stack_trace}")
            failed_scripts.append((script_name, str(e), stack_trace))
            continue
    
    # Print summary
    print("\n" + "="*50)
    print(f"Execution Summary:")
    print(f"Total Scripts: {len(scripts)}")
    print(f"Successful: {success_count}")
    print(f"Failed: {len(failed_scripts)}")
    if failed_scripts:
        print("\nFailed Scripts:")
        for script_name, error, stack_trace in failed_scripts:
            print(f"- {script_name}: {error}")
    print("="*50)
    
    # Return status for potential workflow checks
    return success_count, failed_scripts

if __name__ == "__main__":
    success_count, failed_scripts = run_all_scripts()
    if failed_scripts:
        print("Warning: Some scripts failed, but all scripts were attempted.")
    else:
        print("All scripts completed successfully!")
