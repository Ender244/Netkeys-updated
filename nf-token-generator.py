#!/usr/bin/env python3
"""CLI wrapper for cookie_checker."""

import sys
from cookie_checker import check_cookie


def main():
    cookie_input = sys.stdin.read().strip()
    if not cookie_input:
        print("ERROR: No cookie provided")
        sys.exit(1)

    result = check_cookie(cookie_input, live=False, min_length=50)
    if result['valid'] and result['nftoken']:
        print("Cookie validated successfully")
        print(f"nftoken={result['nftoken']}")
        print(f"Status: VALID")
        print(f"Message: {result['message']}")
        sys.exit(0)

    print(f"Cookie validation failed: {result['message']}")
    print("Status: INVALID")
    sys.exit(1)


if __name__ == '__main__':
    main()
