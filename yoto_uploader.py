"""Legacy entry point kept for backwards compatibility.

Running this module directly (`python yoto_uploader.py`) will behave like the
original script, dispatching to upload mode (no args) or icon mode (URL arg).

New code and the official CLI entry point live in ``yoto_uploader.workflow``
and ``yoto_uploader.cli``.
"""

from yoto_uploader.workflow import main


if __name__ == "__main__":  # pragma: no cover - thin wrapper
    main()
