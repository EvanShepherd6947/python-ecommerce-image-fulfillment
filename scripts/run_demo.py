import sys
from pathlib import Path


# Make the sibling src package importable when this file is run directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.image_order_service import main


if __name__ == "__main__":
    main()
