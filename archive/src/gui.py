import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox
import threading

from archive.src.main import (
    get_available_years, calculate_multi_year_elo,
    get_poll_comparison, calculate_playoff_picture
)
from cfb_integrated_app.src.data_fetcher import update_latest_data, fetch_full_historical_data

class Tooltip:
    """Hover tooltip helper for Tkinter widgets"""
    def __init__(self, widget, text=""):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

class DesktopApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NCAA College Football Advanced ELO System")
        self.geometry("1280x700")
        
        self.years = get_available_years()
        self.selected_year = self.years[-1] if self.years else 2025
        self.sort_criteria = []

        self._apply_styles()
        self._setup_top_bar()

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Home Top 25
        self.tab_top25 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_top25, text="Top 25 (Home)")
        self._setup_top25_tab()

        # Tab 2: Full Power ELO Rankings
        self.tab_full = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_full, text="Full Power ELO Rankings")
        self._setup_full_rankings_tab()

        # Tab 3: Strength of Schedule
        self.tab_sos = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_sos, text="Strength of Schedule")
        self._setup_sos_tab()

        # Tab 4: Team Schedule Detail Search
        self.tab_sched = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_sched, text="Team Schedule Detail")
        self._setup_sched_tab()

        # Tab 5: Poll Comparison
        self.tab_polls = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_polls, text="Poll Comparison")
        self._setup_polls_tab()

        # Tab 6: Playoff Picture
        self.tab_playoff = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_playoff, text="Playoff Picture")
        self._setup_playoff_tab()

        # Tab 7: About
        self.tab_about = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_about, text="About & Formulas")
        self._setup_about_tab()

        # Tab 8: Legal
        self.tab_legal = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_legal, text="Legal & Disclaimers")
        self._setup_legal_tab()

        self.load_data()

    def _apply_styles(self):
        style = ttk.Style(self)
        style.theme_use('alt')
        style.configure("Treeview", background="white", foreground="black", rowheight=28, borderwidth=1)
        style.configure("Treeview.Heading", background="#2A5298", foreground="white", font=('Helvetica', 10, 'bold'))
        style.map("Treeview", background=[('selected', '#ffffcc')], foreground=[('selected', 'black')])

    def _setup_top_bar(self):
        bar = ttk.Frame(self, padding="10")
        bar.pack(fill=tk.X)

        ttk.Label(bar, text="🏈 Season Year: ", font=('Helvetica', 11, 'bold')).pack(side=tk.LEFT)
        self.year_cb = ttk.Combobox(bar, values=self.years, state="readonly", width=10)
        self.year_cb.set(self.selected_year)
        self.year_cb.pack(side=tk.LEFT, padx=5)
        self.year_cb.bind("<<ComboboxSelected>>", self._on_year_changed)

        ttk.Button(bar, text="🔄 Sync Latest Data", command=self._run_sync).pack(side=tk.LEFT, padx=10)
        ttk.Button(bar, text="⏳ Run Full Historical Backfill", command=self._run_backfill).pack(side=tk.LEFT, padx=5)
        ttk.Button(bar, text="♻️ Refresh Data", command=self.load_data).pack(side=tk.LEFT, padx=5)

    def _on_year_changed(self, event=None):
        self.selected_year = int(self.year_cb.get())
        self.load_data()

    def _run_sync(self):
        def task():
            update_latest_data()
            self.after(0, lambda: [self.load_data(), messagebox.showinfo("Sync Complete", "Latest data synced!")])
        threading.Thread(target=task, daemon=True).start()

    def _run_backfill(self):
        def task():
            fetch_full_historical_data()
            self.after(0, lambda: [self.load_data(), messagebox.showinfo("Backfill Complete", "Historical backfill complete!")])
        threading.Thread(target=task, daemon=True).start()

    def load_data(self):
        self.season_data = calculate_multi_year_elo(self.selected_year)
        self._refresh_top25()
        self._refresh_full_rankings()
        self._refresh_sos()
        self._refresh_sched_dropdown()
        self._refresh_polls()
        self._refresh_playoff()

    # TAB 1: TOP 25
    def _setup_top25_tab(self):
        cols = ("Rank", "Team", "Conference", "Record", "Current ELO", "Power ELO", "Preseason Rank")
        self.top25_tree = ttk.Treeview(self.tab_top25, columns=cols, show='headings')
        for c in cols:
            self.top25_tree.heading(c, text=c)
            self.top25_tree.column(c, anchor=tk.CENTER, width=140)
        self.top25_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _refresh_top25(self):
        for i in self.top25_tree.get_children(): self.top25_tree.delete(i)
        teams = self.season_data['teams']
        final_elos = self.season_data['final_elos']
        power_elos = self.season_data['power_elos']
        pre_ranks = self.season_data['preseason_ranks']

        fbs_teams = [t for t in teams if t.division == 'FBS']
        sorted_fbs = sorted(fbs_teams, key=lambda t: final_elos.get(t.team_name, 0.0), reverse=True)[:25]

        for r, t in enumerate(sorted_fbs, start=1):
            name = t.team_name
            w, l = 0, 0
            for gdata in t.schedule:
                if gdata['outcome'] == 'W': w += 1
                elif gdata['outcome'] == 'L': l += 1
            
            self.top25_tree.insert("", tk.END, values=(
                r, name, t.conference, f"{w}-{l}",
                f"{final_elos.get(name, 1500.0):.2f}",
                f"{power_elos.get(name, 1500.0):.2f}",
                pre_ranks.get(name, "N/A")
            ))

    # TAB 2: FULL RANKINGS
    def _setup_full_rankings_tab(self):
        cols = ("Power Rank", "Team", "Division", "Conference", "W-L", "Power ELO", "End ELO", "SoS Rating", "SoS Adj")
        self.full_tree = ttk.Treeview(self.tab_full, columns=cols, show='headings')
        for c in cols:
            self.full_tree.heading(c, text=c)
            self.full_tree.column(c, anchor=tk.CENTER, width=120)
        self.full_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _refresh_full_rankings(self):
        for i in self.full_tree.get_children(): self.full_tree.delete(i)
        teams = [t for t in self.season_data['teams'] if t.division in ('FBS', 'FCS')]
        final_elos = self.season_data['final_elos']
        power_elos = self.season_data['power_elos']
        sos_vals = self.season_data['sos_values']
        sos_adjs = self.season_data['sos_adjs']

        sorted_teams = sorted(teams, key=lambda t: power_elos.get(t.team_name, 0.0), reverse=True)
        for r, t in enumerate(sorted_teams, start=1):
            name = t.team_name
            w, l = 0, 0
            for gdata in t.schedule:
                if gdata['outcome'] == 'W': w += 1
                elif gdata['outcome'] == 'L': l += 1

            self.full_tree.insert("", tk.END, values=(
                r, name, t.division, t.conference, f"{w}-{l}",
                f"{power_elos.get(name, 1500.0):.2f}",
                f"{final_elos.get(name, 1500.0):.2f}",
                f"{sos_vals.get(name, 1300.0):.2f}",
                f"{sos_adjs.get(name, 0.0):+.2f}"
            ))

    # TAB 3: SOS
    def _setup_sos_tab(self):
        week_cols = [f"W{i}" for i in range(1, 17)]
        self.sos_cols = ["Team", "SoS Rank", "SoS Rating", "Wk17 ELO", "SoS Adj", "Power ELO"] + week_cols
        self.sos_tree = ttk.Treeview(self.tab_sos, columns=self.sos_cols, show='headings')
        
        for c in self.sos_cols:
            self.sos_tree.heading(c, text=c)
            width = 120 if c == "Team" else 75
            self.sos_tree.column(c, anchor=tk.CENTER, width=width)
        
        sb = ttk.Scrollbar(self.tab_sos, orient="horizontal", command=self.sos_tree.xview)
        self.sos_tree.configure(xscrollcommand=sb.set)
        
        self.sos_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10,0))
        sb.pack(fill=tk.X, padx=10, pady=(0,10))

    def _refresh_sos(self):
        for i in self.sos_tree.get_children(): self.sos_tree.delete(i)
        teams = [t for t in self.season_data['teams'] if t.division == 'FBS']
        final_elos = self.season_data['final_elos']
        power_elos = self.season_data['power_elos']
        sos_ranks = self.season_data['sos_ranks']
        sos_vals = self.season_data['sos_values']
        sos_adjs = self.season_data['sos_adjs']
        weekly_opps = self.season_data['weekly_opponents']
        weekly_opp_elos = self.season_data['weekly_opp_elos']
        final_ranks = self.season_data['final_ranks']

        sorted_teams = sorted(teams, key=lambda t: power_elos.get(t.team_name, 0.0), reverse=True)
        for t in sorted_teams:
            name = t.team_name
            opps = weekly_opps.get(name, [None]*16)
            o_elos = weekly_opp_elos.get(name, [None]*16)
            
            row = [
                name,
                sos_ranks.get(name, 999),
                f"{sos_vals.get(name, 1300.0):.2f}",
                f"{final_elos.get(name, 1500.0):.2f}",
                f"{sos_adjs.get(name, 0.0):+.2f}",
                f"{power_elos.get(name, 1500.0):.2f}"
            ]

            for i in range(16):
                opp = opps[i] if i < len(opps) else None
                o_elo = o_elos[i] if i < len(o_elos) else None
                if opp and o_elo:
                    opp_r = final_ranks.get(opp, "N/A")
                    row.append(f"{opp} (#{opp_r}|{o_elo:.1f})")
                elif opp:
                    row.append(opp)
                else:
                    row.append("BYE")

            self.sos_tree.insert("", tk.END, values=row)

    # TAB 4: SCHED DETAIL
    def _setup_sched_tab(self):
        ctrl = ttk.Frame(self.tab_sched, padding="10")
        ctrl.pack(fill=tk.X)

        ttk.Label(ctrl, text="Select Team: ").pack(side=tk.LEFT)
        self.team_cb = ttk.Combobox(ctrl, state="readonly", width=25)
        self.team_cb.pack(side=tk.LEFT, padx=5)
        self.team_cb.bind("<<ComboboxSelected>>", self._refresh_sched_table)

        self.sched_info_lbl = ttk.Label(self.tab_sched, text="", font=('Helvetica', 10, 'bold'))
        self.sched_info_lbl.pack(pady=5)

        cols = ("Week", "Opponent", "Outcome", "Score", "Delta ELO", "New ELO", "New Rank", "Game Type")
        self.sched_tree = ttk.Treeview(self.tab_sched, columns=cols, show='headings')
        for c in cols:
            self.sched_tree.heading(c, text=c)
            self.sched_tree.column(c, anchor=tk.CENTER, width=110)
        self.sched_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _refresh_sched_dropdown(self):
        teams = sorted([t.team_name for t in self.season_data['teams'] if t.division in ('FBS', 'FCS') and 'tbd' not in t.team_name.lower()])
        self.team_cb['values'] = teams
        if teams:
            self.team_cb.set(teams[0])
            self._refresh_sched_table()

    def _refresh_sched_table(self, event=None):
        for i in self.sched_tree.get_children(): self.sched_tree.delete(i)
        tname = self.team_cb.get()
        if not tname: return

        team_obj = next((t for t in self.season_data['teams'] if t.team_name == tname), None)
        if not team_obj: return

        pre_r = self.season_data['preseason_ranks'].get(tname, "N/A")
        pre_e = self.season_data['preseason_elos'].get(tname, 1500.0 if team_obj.division == 'FBS' else 1100.0)
        end_e = self.season_data['final_elos'].get(tname, 1500.0)

        self.sched_info_lbl.config(text=f"{tname} | Conf: {team_obj.conference} | Div: {team_obj.division} | Preseason Rank: #{pre_r} | Preseason ELO: {pre_e:.2f} | End ELO: {end_e:.2f}")

        for gdata in team_obj.schedule:
            delta_str = f"{gdata.get('delta', 0.0):+.3f}"
            new_elo = f"{gdata.get('new_elo', 0.0):.3f}"
            new_rank = str(gdata.get('new_rank', "-"))
            gtype = gdata.get('game_type', 'Regular')
            wk_disp = gdata.get('display_week', gdata.get('week', ''))

            item = self.sched_tree.insert("", tk.END, values=(
                wk_disp, gdata['opponent_name'], gdata['outcome'],
                gdata.get('score_str', f"{gdata.get('team_score', '')}-{gdata.get('opp_score', '')}"),
                delta_str, new_elo, new_rank, gtype
            ))
            if gdata['outcome'] == "W": self.sched_tree.item(item, tags=('win',))
            elif gdata['outcome'] == "L": self.sched_tree.item(item, tags=('loss',))

        self.sched_tree.tag_configure('win', foreground='green')
        self.sched_tree.tag_configure('loss', foreground='red')

    # TAB 5: POLLS
    def _setup_polls_tab(self):
        ctrl = ttk.Frame(self.tab_polls, padding="10")
        ctrl.pack(fill=tk.X)
        ttk.Label(ctrl, text="Select Week: ").pack(side=tk.LEFT)
        self.poll_wk_sb = tk.Spinbox(ctrl, from_=1, to=16, width=5, command=self._refresh_polls)
        self.poll_wk_sb.pack(side=tk.LEFT, padx=5)

        cols = ("Rank", "AP Poll", "Coaches Poll", "CFP Committee", "ELO Top 25")
        self.polls_tree = ttk.Treeview(self.tab_polls, columns=cols, show='headings')
        for c in cols:
            self.polls_tree.heading(c, text=c)
            self.polls_tree.column(c, anchor=tk.CENTER, width=150)
        self.polls_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _refresh_polls(self):
        for i in self.polls_tree.get_children(): self.polls_tree.delete(i)
        try: wk = int(self.poll_wk_sb.get())
        except: wk = 16
        
        comp_data = get_poll_comparison(self.selected_year, week=wk)
        for row in comp_data:
            self.polls_tree.insert("", tk.END, values=(
                row["Rank"], row["AP Poll"], row["Coaches Poll"], row["CFP Committee"], row["ELO Top 25"]
            ))

    # TAB 6: PLAYOFF PICTURE
    def _setup_playoff_tab(self):
        ctrl = ttk.Frame(self.tab_playoff, padding="10")
        ctrl.pack(fill=tk.X)
        ttk.Label(ctrl, text="Ranking Metric Source: ").pack(side=tk.LEFT)
        self.playoff_src_cb = ttk.Combobox(ctrl, values=["ELO", "AP", "Coaches", "CFP"], state="readonly", width=10)
        self.playoff_src_cb.set("ELO")
        self.playoff_src_cb.pack(side=tk.LEFT, padx=5)
        self.playoff_src_cb.bind("<<ComboboxSelected>>", self._refresh_playoff)

        lbl = ttk.Label(self.tab_playoff, text="Official 12-Team CFB Playoff Bracket", font=('Helvetica', 11, 'bold'))
        lbl.pack(pady=5)

        cols = ("Seed", "Team", "Conference", "Poll Rank", "Playoff Status")
        self.playoff_tree = ttk.Treeview(self.tab_playoff, columns=cols, show='headings', height=12)
        for c in cols:
            self.playoff_tree.heading(c, text=c)
            self.playoff_tree.column(c, anchor=tk.CENTER, width=150)
        self.playoff_tree.pack(fill=tk.X, padx=10, pady=5)

        m_cols = ("Matchup", "Game", "Location")
        self.matchup_tree = ttk.Treeview(self.tab_playoff, columns=m_cols, show='headings', height=8)
        for c in m_cols:
            self.matchup_tree.heading(c, text=c)
            self.matchup_tree.column(c, anchor=tk.CENTER, width=200)
        self.matchup_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    def _refresh_playoff(self, event=None):
        for i in self.playoff_tree.get_children(): self.playoff_tree.delete(i)
        for i in self.matchup_tree.get_children(): self.matchup_tree.delete(i)

        src = self.playoff_src_cb.get()
        p_table, matchups = calculate_playoff_picture(self.selected_year, ranking_source=src)

        for r in p_table:
            self.playoff_tree.insert("", tk.END, values=(r["Seed"], r["Team"], r["Conference"], r["Poll Rank"], r["Playoff Status"]))

        for m in matchups:
            self.matchup_tree.insert("", tk.END, values=(m["Matchup"], m["Game"], m["Location"]))

    # TAB 7: ABOUT
    def _setup_about_tab(self):
        txt = tk.Text(self.tab_about, wrap=tk.WORD, font=('Helvetica', 10))#, padding=15)
        txt.insert(tk.END, """NCAA COLLEGE FOOTBALL ADVANCED ELO SYSTEM
===================================================

PURPOSE:
This application models non-linear rating evolution for College Football teams. It calculates team ratings dynamically taking into account opponent quality, point differential, upset factor, and strength of schedule.

MATHEMATICAL FORMULAS:
----------------------
1. K-factor Decay:
   Keff = max(K_min, K0 * 0.95^(Week - 1))

2. Win Expectancy:
   Et = 1 / (1 + 10^((ELO_opp - ELO_team) / 400))

3. Margin of Victory Factor:
   m = ln(1 + |Score_team - Score_opp| / 400)

4. Upset Boost:
   U = min(1 + beta * (|Rank_team - Rank_opp| / (N - 1))^rho, 1 + beta_max)

5. Rating Delta:
   Delta ELO = Keff * (St - Et) * (1 + gamma * m) * U

6. Strength of Schedule (SoS) & Power ELO:
   SoS = Average(Opponent Final ELOs)
   SoS_Adj = (SoS - 1500) * 0.5
   Power ELO = Final ELO + SoS_Adj
""")
        txt.config(state=tk.DISABLED)
        txt.pack(fill=tk.BOTH, expand=True)

    # TAB 8: LEGAL
    def _setup_legal_tab(self):
        txt = tk.Text(self.tab_legal, wrap=tk.WORD, font=('Helvetica', 10))#, padding=15)
        txt.insert(tk.END, """LEGAL DISCLAIMERS & EXPERIMENTAL NOTICE
========================================

1. EXPERIMENTAL USE:
   This software is free of charge and created for educational and experimental evaluation only.

2. DATA ATTRIBUTION:
   Scoreboard data, schedules, logos, and team metadata are retrieved via public ESPN API endpoints.
   All university names, team nicknames, logos, and marks are trademarks of their respective NCAA rights holders.

3. WARRANTY:
   PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.
""")
        txt.config(state=tk.DISABLED)
        txt.pack(fill=tk.BOTH, expand=True)

def start_gui():
    app = DesktopApp()
    app.mainloop()

if __name__ == "__main__":
    start_gui()