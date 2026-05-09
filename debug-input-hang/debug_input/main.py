#!/usr/bin/env python3
"""Mimics clp_package_utils.scripts.start_clp — the Python entry point inside the container."""

import os
import sys


def main():
    print("=" * 60)
    print("DIAGNOSTIC: Inside the Docker container now")
    print("=" * 60)

    # 1. Check shell interactivity flags
    print(f"\n--- Shell interactivity (from host) ---")
    print(f"  bash $- = {os.environ.get('_BASH_INTERACTIVE', 'unknown')}")

    # 2. Check TTY status
    print(f"\n--- TTY / stdin status ---")
    print(f"  sys.stdin.isatty()       = {sys.stdin.isatty()}")
    print(f"  sys.stdout.isatty()      = {sys.stdout.isatty()}")
    print(f"  sys.stderr.isatty()      = {sys.stderr.isatty()}")

    # 3. Check terminal device
    print(f"\n--- Terminal device ---")
    try:
        tty_name = os.ttyname(0)
        print(f"  os.ttyname(0) (stdin)    = {tty_name}")
    except OSError as e:
        print(f"  os.ttyname(0) (stdin)    = OSError: {e}")

    # 4. Check TERM and related env vars
    print(f"\n--- Environment ---")
    print(f"  TERM                     = {os.environ.get('TERM', '<unset>')}")
    print(f"  PYTHONIOENCODING         = {os.environ.get('PYTHONIOENCODING', '<unset>')}")
    print(f"  DOCKER_TTY               = {os.environ.get('DOCKER_TTY', '<unset>')}")
    print(f"  HOME                     = {os.environ.get('HOME', '<unset>')}")

    # 5. Check file descriptors
    print(f"\n--- File descriptors ---")
    for fd, name in [(0, "stdin"), (1, "stdout"), (2, "stderr")]:
        try:
            mode = os.fstat(fd).st_mode
            print(f"  fd {fd} ({name}) mode      = {oct(mode)}")
        except OSError as e:
            print(f"  fd {fd} ({name})            = OSError: {e}")

    # 6. The actual input() call that hangs in the real CLP
    print(f"\n--- Attempting input() ---")
    print("If this hangs, you've reproduced the bug.")
    try:
        response = input("Type something and press Enter: ").strip()
        print(f"  You typed: '{response}'")
    except EOFError:
        print("  Got EOFError — stdin was closed / not connected")
    except KeyboardInterrupt:
        print("  Got KeyboardInterrupt")
    except Exception as e:
        print(f"  Got unexpected exception: {type(e).__name__}: {e}")

    print("\nDone. If you see this, input() did NOT hang.")


if "__main__" == __name__:
    main()
