import importlib
import os
import sys
import time
from pathlib import Path
import traceback

# Add current directory (where run_all_scripts.py is located) to Python path
code_dir = Path(__file__).parent
sys.path.append(str(code_dir))

# Log the Python path for debugging
print(f"Python path: {sys.path}")

# List of script names (with .py extension)
scripts = [
    "Gross Domestic Product.py",
    "GDP Growth Rate.py",
    "Inflation Rate (CPI).py",
    "Unemployment Rate.py",
    "Interest Rates (Federal Funds Rate).py",
    "Money Supply (M2).py",
    "Consumer Confidence Index.py",
    "Business Confidence Index.py",
    "Retail Sales.py",
    "Industrial Production.py",
    "Capacity Utilization.py",
    "Purchasing Managers' Index (PMI).py",
    "Housing Starts.py",
    "Building Permits.py",
    "Trade Balance.py",
    "Current Account Balance (OECD).py",
    "Foreign Direct Investment (FDI) (UNCTAD).py",
    "Government Budget Balance (OECD).py",
    "Public Debt Levels (IMF).py",
    "Exchange Rates (Investing.com).py"
]

def run_all_scripts():
    success_count = 0
    failed_scripts = []
    
    for script_name in scripts:
        start_time = time.time()
        # Remove .py for display purposes in logs
        display_name = script_name.replace(".py", "")
        print(f"\n[START] Running {display_name}...")
        try:
            # Convert script name to module name (remove .py, replace spaces and special chars)
            module_name = script_name.replace(".py", "").replace(" ", "_").replace("'", "").replace("(", "").replace(")", "").replace(".", "")
            print(f"Attempting to import module: {module_name}")
            # Import the module
            module = importlib.import_module(module_name)
            # Scripts execute their main logic on import
            elapsed_time = time.time() - start_time
            print(f"[SUCCESS] Completed {display_name} in {elapsed_time:.2f} seconds")
            success_count += 1
        except Exception as e:
            elapsed_time = time.time() - start_time
            error_message = f"[ERROR] Failed {display_name} in {elapsed_time:.2f} seconds: {str(e)}"
            stack_trace = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
            print(error_message)
            print(f"[STACK TRACE]\n{stack_trace}")
            failed_scripts.append((display_name, str(e), stack_trace))
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
