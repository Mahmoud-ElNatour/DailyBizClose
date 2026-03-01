import traceback

print("starting serve.py...")

try:
    from waitress import serve
    print("waitress imported")

    from app import app
    print("imported app from app.py:", app)

    print("Serving on http://127.0.0.1:5000")
    serve(app, host="127.0.0.1", port=5000)

except Exception:
    print("\nFAILED:")
    traceback.print_exc()

input("\nPress Enter to exit...")
