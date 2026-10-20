#!/usr/bin/env python3
"""Optional local Studio; deliberately separate from the trusted controller entry."""
from studio.server import main

if __name__ == '__main__':
    raise SystemExit(main())
