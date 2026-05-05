#!/usr/bin/env python3
"""
Nargan Mapper - Entry Point
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "9004"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    print("=" * 50)
    print("  Nargan Mapper - Industrial Datasheet Mapper")
    print("=" * 50)
    print(f"  Starting server at http://{host}:{port}")
    print(f"  Debug mode: {debug}")
    print("=" * 50)
    
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug",
    )

if __name__ == "__main__":
    main()