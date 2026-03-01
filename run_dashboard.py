#!/usr/bin/env python
"""
Launch the Sentinel Dashboard.
Usage: streamlit run run_dashboard.py
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run the dashboard
from src.dashboard.app import main

if __name__ == "__main__":
    main()
