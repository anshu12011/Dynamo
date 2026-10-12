"""Run local mutation testing against all 20 rate limiter mutants."""

import os
import sys
import subprocess
from pathlib import Path

APP_DIR = Path("/app")
TEST_FILE = APP_DIR / "test_limiter.py"


def main():
    if not TEST_FILE.exists():
        print(f"Error: {TEST_FILE} does not exist.")
        sys.exit(1)

    killed = []
    survived = []

    print("Running mutation tests against 20 rate limiter mutants...\n")

    for i in range(1, 21):
        mutant_name = f"mutant_{i:02d}"
        env = os.environ.copy()
        env["LIMITER_MODULE"] = f"mutants.{mutant_name}"

        try:
            res = subprocess.run(
                [sys.executable, "-m", "pytest", str(TEST_FILE), "-q"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=45,
            )
            if res.returncode != 0:
                killed.append(mutant_name)
                print(f"  [KILL] {mutant_name}")
            else:
                survived.append(mutant_name)
                print(f"  [SURVIVE] {mutant_name}")
        except subprocess.TimeoutExpired:
            killed.append(mutant_name)
            print(f"  [KILL - TIMEOUT] {mutant_name}")

    print("\n----------------------------------------")
    print(f"Mutation score: {len(killed)}/20 killed")
    if survived:
        print(f"Surviving mutants ({len(survived)}): {', '.join(survived)}")
        sys.exit(1)
    else:
        print("Success! All 20 mutants were killed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
