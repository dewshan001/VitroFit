"""Compatibility shim: VitroFit.API launches the service with `python server.py`.
The real entry point is main.py."""

from main import HOST, PORT, main

if __name__ == "__main__":
    main()
