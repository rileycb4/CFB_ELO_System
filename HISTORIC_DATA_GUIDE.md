# Guide: Running Full Historical College Football Data Backfills

This guide explains how to initiate a complete historical backfill of NCAA College Football data (from **2001 to present day**, covering **FBS, FCS, Division II, and Division III**) into your local SQLite database (`resources/cfb_elo.db`).

---

## Option 1: Command-Line Interface (Terminal)

You can run the full historical data backfill at any time directly from your terminal.

1. Open your terminal / command prompt in the project root directory:
   ```bash
   cd c:\Users\riley\Documents\Coding_Projects\CFB_ELO_System
   ```

2. Execute the full historical backfill command:
   ```bash
   python -m src.data_fetcher --full
   ```

3. The script will iterate through each season from 2001 to the current year, fetching:
   - Complete regular season schedules & scores (Weeks 1–16)
   - Postseason / Bowl games / Championship games
   - Team status changes (division shifts and conference realignment)
   - Historical AP, Coaches, and CFP poll rankings

4. To run a fast delta update for the current season only, execute:
   ```bash
   python -m src.data_fetcher --update
   ```

---

## Option 2: Streamlit Web App Interface

1. Launch the Streamlit Web Application:
   ```bash
   streamlit run src/app.py
   ```

2. At the top of the page in the header section, click the **"Run Full Historical Backfill"** button.
3. A progress indicator will display while historical seasons are populated into your SQLite database.

---

## Option 3: Local Desktop GUI Interface

1. Launch the Desktop GUI Application:
   ```bash
   python src/main.py
   ```

2. Click **Data Tools** -> **Fetch Full Historical Data (2001–Present)** in the top menu bar or click the **"Full Backfill"** button in the header.

---

## Technical Details & Redundancy

- **Database Path**: `resources/cfb_elo.db`
- **Offline Backup XML**: `resources/FBS_list.xml` (automatically synced after each pull)
- **Automatic Sync**: The system includes a background scheduler that runs a delta update daily at 4:00 AM to keep active season scores up to date.
