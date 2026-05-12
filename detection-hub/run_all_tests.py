import os
import subprocess

def run_tests():
    print("=" * 60)
    print("STARTING A.T.V.D SYSTEM TEST SUITE")
    print("=" * 60)
    
    print("\n[1/2] RUNNING AI CORE ALGORITHMS TEST...")
    # Run the AI script
    result_ai = subprocess.run(["python", "test_ai_core.py"], capture_output=True, text=True, encoding="utf-8")
    print(result_ai.stdout)
    if result_ai.stderr:
        print(f"Errors:\n{result_ai.stderr}")
    
    print("\n[2/2] RUNNING BACKEND API ENDPOINT UNIT TESTS...")
    # Run pytest
    result_pytest = subprocess.run(["pytest", "test_endpoints.py", "-v", "--disable-warnings"], capture_output=True, text=True, encoding="utf-8")
    print(result_pytest.stdout)
    if result_pytest.stderr:
        print(f"Errors:\n{result_pytest.stderr}")

    print("=" * 60)
    if result_ai.returncode == 0 and result_pytest.returncode == 0:
        print("ALL TESTS PASSED! THE SYSTEM IS PRODUCTION-READY.")
    else:
        print("SOME TESTS FAILED. PLEASE REVIEW THE LOGS ABOVE.")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
