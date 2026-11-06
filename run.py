import uvicorn
import webbrowser
import sys

if __name__ == "__main__":
    print("=" * 60)
    print("  PROJECT UDYAM DIGITAL — AIRTEL BUSINESS ONBOARDING")
    print("  Airtel SYNC Hackathon 2026 — Enterprise Track A")
    print("=" * 60)
    print("Starting server at http://127.0.0.1:8000 ...")
    print("Press CTRL+C to stop.\n")
    
    # Run uvicorn server
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

