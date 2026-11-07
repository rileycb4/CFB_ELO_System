"""Optional Tkinter preview launcher; Streamlit is the primary interface."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.data_adapter import available_years, load_dashboard_data
from ui.rankings import show_desktop


def main():
    years = available_years()
    year = years[-1]
    data = load_dashboard_data(year)
    # The Tk renderer uses the same data and offers schedule/H2H popups.
    show_desktop(data["teams"])


if __name__ == "__main__":
    main()
