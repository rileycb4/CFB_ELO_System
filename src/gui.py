import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from formula import calculate_delta_elo as dt_elo

class TeamViewer(tk.Tk):
    def __init__(self, teams):
        super().__init__()
        self.title("NCAA Advanced Team System")
        self.geometry("1200x800")
        self.teams = teams
        self.sort_criteria = [] 
        
        # --- Apply the Styles ---
        self._apply_styles()
        
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # Tab 1: Team Viewer
        self.tab_viewer = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_viewer, text="Team Viewer")
        self._setup_viewer_tab()

        # Tab 2: Standings
        self.tab_standings = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_standings, text="Standings")
        self._setup_standings_tab()

        # Tab 3: Rankings
        self.tab_rankings = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_rankings, text="Rankings")
        self._setup_rankings_tab()

        # Tab 4: Strength of Schedule
        self.tab_sos = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_sos, text="Strength of Schedule")
        self._setup_sos_tab()

    def _apply_styles(self):
        style = ttk.Style(self)
        style.theme_use('alt') 

        # --- ADD THESE 3 LINES ---
        self.standard_font = tkfont.nametofont("TkDefaultFont")
        self.bold_font = self.standard_font.copy()
        self.bold_font.configure(weight="bold")
        # -------------------------

        # Configure the Body (Cells and Rows)
        style.configure("Treeview", 
                        background="white", 
                        foreground="black", 
                        rowheight=30, 
                        fieldbackground="white",
                        borderwidth=1,
                        relief="solid")

        # Configure the Headings
        style.configure("Treeview.Heading", 
                        background="#dddddd", 
                        foreground="black",
                        relief="solid", 
                        borderwidth=1,
                        font=('Helvetica', 10, 'bold'))

        # Custom Highlight Color (Faded Yellow)
        style.map("Treeview", 
                  background=[('selected', '#ffffcc')],
                  foreground=[('selected', 'black')])

    def _setup_viewer_tab(self):
        search_frame = ttk.Frame(self.tab_viewer, padding="10")
        search_frame.pack(fill=tk.X)
        ttk.Label(search_frame, text="Search: ").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search_change)
        ttk.Entry(search_frame, textvariable=self.search_var, width=30).pack(side=tk.LEFT, padx=5)
        
        # Wrapper frame for the 1px black outer border
        container = tk.Frame(self.tab_viewer, background="black", highlightbackground="black", highlightthickness=1)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("Rank", "Team", "Conference", "ELO")
        # Removed highlightthickness from the Treeview constructor
        self.tree = ttk.Treeview(container, columns=cols, show='headings')
        for col in cols:
            self.tree.heading(col, text=col, command=lambda c=col: self._update_sort_stack(self.tree, c))
            self.tree.column(col, anchor=tk.CENTER)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self._on_viewer_double_click)
        self._load_viewer_data(self.teams)

    def _setup_standings_tab(self):
        ctrl = ttk.Frame(self.tab_standings, padding="10")
        ctrl.pack(fill=tk.X)
        ttk.Label(ctrl, text="Conference: ").pack(side=tk.LEFT)
        confs = sorted(list(set(t.conference for t in self.teams)))
        self.conf_selector = ttk.Combobox(ctrl, values=confs, state="readonly")
        self.conf_selector.pack(side=tk.LEFT, padx=5)
        self.conf_selector.bind("<<ComboboxSelected>>", self._update_standings)

        container = tk.Frame(self.tab_standings, background="black", highlightbackground="black", highlightthickness=1)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.stand_tree = ttk.Treeview(container, columns=("Team", "W", "L", "Pct"), show='headings')
        for col in ("Team", "W", "L", "Pct"):
            self.stand_tree.heading(col, text=col, command=lambda c=col: self._update_sort_stack(self.stand_tree, c))
            self.stand_tree.column(col, anchor=tk.CENTER)
        
        self.stand_tree.pack(fill=tk.BOTH, expand=True)
        self.stand_tree.bind("<Double-1>", self._on_standings_double_click)
        self.champ_info = ttk.Label(self.tab_standings, text="Championship Result:", font=('Helvetica', 10, 'bold'))
        self.champ_info.pack(pady=10)

    def _setup_rankings_tab(self):
        container = tk.Frame(self.tab_rankings, background="black", highlightbackground="black", highlightthickness=1)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        week_cols = [f"W{i}" for i in range(1, 17)] 
        # Separate Rank and ELO columns
        self.rank_cols = ["Team", "Rank", "ELO"] + week_cols 
        
        self.rank_tree = ttk.Treeview(container, columns=self.rank_cols, show='headings')
        
        for col in self.rank_cols:
            # Bind the sorting command to every single column header
            self.rank_tree.heading(col, text=col, command=lambda c=col: self._update_sort_stack(self.rank_tree, c))
            
            # Adjust widths to fit nicely
            if col == "Team": width = 135
            elif col == "Rank": width = 50
            elif col == "ELO": width = 75
            else: width = 65
                
            self.rank_tree.column(col, width=width, anchor=tk.CENTER)

        self.rank_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(container, orient="vertical", command=self.rank_tree.yview)
        self.rank_tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.rank_tree.bind("<Double-1>", self._on_rankings_double_click)

    # --- Add this new method to the class ---
    def _setup_sos_tab(self):
        container = tk.Frame(self.tab_sos, background="black", highlightbackground="black", highlightthickness=1)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        week_cols = [f"W{i}" for i in range(1, 17)]
        self.sos_cols = ["Team", "SoS", "SoS Rank", "Wk17 ELO", "SoS Adj", "Power ELO"] + week_cols
        
        self.sos_tree = ttk.Treeview(container, columns=self.sos_cols, show='headings')
        
        # --- NEW: Define exactly which columns should be sortable ---
        sortable_cols = ["Team", "SoS", "SoS Rank", "Wk17 ELO", "SoS Adj", "Power ELO"]
        
        for col in self.sos_cols:
            # Only bind the sorting command to the specific columns requested
            if col in sortable_cols:
                self.sos_tree.heading(col, text=col, command=lambda c=col: self._update_sort_stack(self.sos_tree, c))
            else:
                self.sos_tree.heading(col, text=col) # Static header for Wk1-Wk16
            
            # Adjust column widths dynamically
            if col == "Team": width = 135
            elif col.startswith("W") and len(col) <= 3: width = 60 # W1-W16
            else: width = 80
            
            self.sos_tree.column(col, width=width, anchor=tk.CENTER)

        self.sos_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = ttk.Scrollbar(container, orient="vertical", command=self.sos_tree.yview)
        self.sos_tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind the double click to the schedule popup
        self.sos_tree.bind("<Double-1>", self._on_sos_double_click)

    # --- Formula & Ranking Logic ---
    def _calculate_rankings(self):
        """Processes the formula and builds SoS metrics using Final opponent ELOs."""
        working_elos = {t.team_name: t.ELO for t in self.teams}
        working_ranks = {t.team_name: t.ranking for t in self.teams}
        weekly_deltas = {t.team_name: [0.0] * 16 for t in self.teams}
        
        # --- CHANGED: Track Opponent Names instead of their active ELO ---
        weekly_opp_names = {t.team_name: [None] * 16 for t in self.teams}
        
        for t in self.teams: t.weekly_history = {}

        seen_games = set()
        games_by_week = {}
        for team in self.teams:
            for week, data in team.schedule.items():
                opp_name = data["opponent_name"]
                game_id = tuple(sorted((team.team_name, opp_name)) + [week])
                if game_id not in seen_games:
                    games_by_week.setdefault(week, []).append({
                        'week': week, 't1': team.team_name, 't2': opp_name,
                        's1': data["team"]["score"], 's2': data["opponent"]["score"]
                    })
                    seen_games.add(game_id)
        
        # Sequential Calculation (Week by Week)
        for week in sorted(games_by_week.keys()):
            # Re-rank at start of week
            sorted_by_elo = sorted(working_elos.items(), key=lambda item: item[1], reverse=True)
            for current_rank, (team_name, _) in enumerate(sorted_by_elo, start=1):
                working_ranks[team_name] = current_rank
            
            current_week_deltas = {}

            # Process games
            for g in games_by_week[week]:
                t1_name, t2_name = g['t1'], g['t2']
                t1_in_fbs = t1_name in working_elos
                t2_in_fbs = t2_name in working_elos

                e1 = working_elos[t1_name] if t1_in_fbs else 1300.0
                e2 = working_elos[t2_name] if t2_in_fbs else 1300.0
                r1 = working_ranks[t1_name] if t1_in_fbs else 200
                r2 = working_ranks[t2_name] if t2_in_fbs else 200
                
                # --- CHANGED: Record Opponent NAME to look up their final ELO later ---
                if t1_in_fbs and 0 < g['week'] <= 16:
                    weekly_opp_names[t1_name][g['week']-1] = t2_name
                if t2_in_fbs and 0 < g['week'] <= 16:
                    weekly_opp_names[t2_name][g['week']-1] = t1_name

                # Math Deltas
                d1 = dt_elo(e1, e2, r1, r2, "W" if g['s1'] > g['s2'] else "L", g['s1'], g['s2'], g['week'])
                d2 = dt_elo(e2, e1, r2, r1, "W" if g['s2'] > g['s1'] else "L", g['s2'], g['s1'], g['week'])
                
                # Apply Deltas
                if t1_in_fbs:
                    working_elos[t1_name] += d1
                    current_week_deltas[t1_name] = current_week_deltas.get(t1_name, 0.0) + d1
                    if 0 < g['week'] <= 16: weekly_deltas[t1_name][g['week']-1] += d1
                        
                if t2_in_fbs:
                    working_elos[t2_name] += d2
                    current_week_deltas[t2_name] = current_week_deltas.get(t2_name, 0.0) + d2
                    if 0 < g['week'] <= 16: weekly_deltas[t2_name][g['week']-1] += d2

            # Re-rank at END of week to capture the new standings for history
            sorted_by_elo = sorted(working_elos.items(), key=lambda item: item[1], reverse=True)
            end_of_week_ranks = {team_name: rank for rank, (team_name, _) in enumerate(sorted_by_elo, start=1)}

            # Save history
            for t_name, total_delta in current_week_deltas.items():
                team_obj = next(t for t in self.teams if t.team_name == t_name)
                team_obj.weekly_history[week] = {
                    'delta': total_delta, 'new_elo': working_elos[t_name], 'new_rank': end_of_week_ranks[t_name]
                }

        # ==========================================
        # TAB REFRESH: RANKINGS
        # ==========================================
        for item in self.rank_tree.get_children(): self.rank_tree.delete(item)
        
        # Re-fetch final ranks for display
        sorted_by_elo = sorted(working_elos.items(), key=lambda item: item[1], reverse=True)
        for final_rank, (team_name, _) in enumerate(sorted_by_elo, start=1):
            working_ranks[team_name] = final_rank
            
        ranking_data = [
            {"name": t.team_name, "rank": working_ranks[t.team_name], "total": working_elos[t.team_name], "deltas": weekly_deltas[t.team_name]} 
            for t in self.teams
        ]
        ranking_data.sort(key=lambda x: x['total'], reverse=True)

        for data in ranking_data:
            display = [f"{d:+.1f}" if d != 0 else "" for d in data['deltas']]
            self.rank_tree.insert("", tk.END, values=[data['name'], data['rank'], f"{data['total']:.3f}"] + display, tags=("bold_row",))

        # ==========================================
        # TAB REFRESH: STRENGTH OF SCHEDULE
        # ==========================================
        for item in self.sos_tree.get_children(): self.sos_tree.delete(item)
        
        sos_data = []
        OMEGA = 0.5
        
        for t in self.teams:
            name = t.team_name
            
            # --- CHANGED: Resolve Final ELOs for each opponent played ---
            opp_final_elos = []
            for opp_name in weekly_opp_names[name]:
                if opp_name is not None:
                    # Look up the final calculated ELO (Default to 1300.0 if FCS)
                    opp_final_elos.append(working_elos.get(opp_name, 1300.0))
                else:
                    opp_final_elos.append(None)
            
            # Filter out the "None" values (BYE weeks) to get true average
            played_elos = [elo for elo in opp_final_elos if elo is not None]
            
            sos = sum(played_elos) / len(played_elos) if played_elos else 1300.0
            wk17_elo = working_elos[name]
            sos_adj = (sos - 1500) * OMEGA
            power_elo = wk17_elo + sos_adj
            
            sos_data.append({
                "name": name, "sos": sos, "wk17_elo": wk17_elo, 
                "sos_adj": sos_adj, "power_elo": power_elo, "weekly_opps": opp_final_elos
            })
            
        # 1. Determine SoS Rank
        sos_data.sort(key=lambda x: x['sos'], reverse=True)
        for rank, data in enumerate(sos_data, start=1):
            data['sos_rank'] = rank
            
        # 2. Sort by Power ELO descending for default display
        sos_data.sort(key=lambda x: x['power_elo'], reverse=True)
        
        for data in sos_data:
            display_opps = [f"{elo:.1f}" if elo is not None else "" for elo in data['weekly_opps']]
            
            row_vals = [
                data['name'], 
                f"{data['sos']:.2f}", 
                data['sos_rank'], 
                f"{data['wk17_elo']:.2f}", 
                f"{data['sos_adj']:+.2f}", 
                f"{data['power_elo']:.2f}"
            ] + display_opps
            
            self.sos_tree.insert("", tk.END, values=row_vals)

    # --- Navigation & Events ---
    def _on_tab_changed(self, event):
        selected_tab = self.notebook.tab(self.notebook.select(), "text")
        if selected_tab == "Rankings":
            self.sort_criteria = [("Rank", True)]
            self._calculate_rankings()
            self._update_header_arrows(self.rank_tree)
        elif selected_tab == "Strength of Schedule":
            self.sort_criteria = [("Power ELO", True)]
            self._calculate_rankings()
            self._update_header_arrows(self.rank_tree)
        elif selected_tab == "Standings":
            self.sort_criteria = [("W", True)]
            self._update_header_arrows(self.stand_tree)
            if self.conf_selector.get():
                self._update_standings()

    # --- Sorting Logic ---
    def _update_sort_stack(self, tree, col_name):
        is_reverse = False
        if self.sort_criteria and self.sort_criteria[0][0] == col_name:
            is_reverse = not self.sort_criteria[0][1]
            self.sort_criteria.pop(0)
        else:
            for i, (c, rev) in enumerate(self.sort_criteria):
                if c == col_name:
                    is_reverse = rev
                    self.sort_criteria.pop(i)
                    break
        self.sort_criteria.insert(0, (col_name, is_reverse))
        self.sort_criteria = self.sort_criteria[:3]
        self._apply_sort(tree)
        self._update_header_arrows(tree)

    def _apply_sort(self, tree):
        for col_name, reverse in reversed(self.sort_criteria):
            def get_val(k):
                v = tree.set(k, col_name)
                try: return float(v)
                except: return v.lower()
            children = list(tree.get_children(""))
            children.sort(key=get_val, reverse=reverse)
            for i, k in enumerate(children): tree.move(k, "", i)

    def _update_header_arrows(self, tree):
        all_cols = tree["columns"]
        for col in all_cols:
            tree.heading(col, text=col)
        if self.sort_criteria:
            primary, rev = self.sort_criteria[0]
            if primary in all_cols:
                tree.heading(primary, text=primary + (" ▼" if rev else " ▲"))

    # --- Shared Handlers ---
    def _on_viewer_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            name = self.tree.item(item, 'values')[1]
            team = next(t for t in self.teams if t.team_name == name)
            self._open_schedule(team)

    def _on_standings_double_click(self, event):
        item = self.stand_tree.identify_row(event.y)
        if item:
            name = self.stand_tree.item(item, 'values')[0]
            team = next(t for t in self.teams if t.team_name == name)
            self._open_schedule(team)

    def _open_schedule(self, team):
        """Builds the popup schedule window from the new dictionary."""
        wins, losses = 0, 0
        
        for week, data in team.schedule.items():
            if not data.get("is_champ", False):
                if data["outcome"] == 'W': wins += 1
                elif data["outcome"] == 'L': losses += 1
        
        rk_disp = team.ranking if team.ranking is not None else "N/A"
        elo_disp = f"{team.ELO:.3f}" if team.ELO is not None else "0.000"
        
        win = tk.Toplevel(self)
        win.title(f"Schedule: {team.team_name} [{wins}-{losses} | Rk. {rk_disp} | ELO: {elo_disp}]")
        win.geometry("600x450")
        
        container = tk.Frame(win, background="black", highlightbackground="black", highlightthickness=1)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        cols = ("Week", "Opponent", "Outcome", "Score", "Type")
        tree = ttk.Treeview(container, columns=cols, show='headings')
        for c in cols: 
            tree.heading(c, text=c)
            tree.column(c, anchor=tk.CENTER)
            
        # Sort the dictionary keys so the schedule displays chronologically
        for week in sorted(team.schedule.keys()):
            data = team.schedule[week]
            game_type = "Champ" if data.get("is_champ", False) else "Regular"
            score_str = f"{data['team']['score']}-{data['opponent']['score']}"
            
            item = tree.insert("", tk.END, values=(week, data['opponent_name'], data['outcome'], score_str, game_type))
            
            # Apply color coding directly based on outcome
            if data['outcome'] == "W":
                tree.tag_configure('win', foreground='green')
                tree.item(item, tags=('win',))
            elif data['outcome'] == "L":
                tree.tag_configure('loss', foreground='red')
                tree.item(item, tags=('loss',))
                
        tree.pack(fill=tk.BOTH, expand=True)

    def _load_viewer_data(self, team_list):
        for i in self.tree.get_children(): self.tree.delete(i)
        for t in team_list:
            self.tree.insert("", tk.END, values=(t.ranking or "N/A", t.team_name, t.conference, f"{t.ELO:.3f}"))

    def _on_search_change(self, *args):
        query = self.search_var.get().lower()
        filtered = [t for t in self.teams if query in t.team_name.lower() or query in t.conference.lower()]
        self._load_viewer_data(filtered)
        self._apply_sort(self.tree)

    def _update_standings(self, event=None):
        """Calculates W-L based on the new dictionary schedule."""
        conf = self.conf_selector.get()
        if not conf: return
        
        for i in self.stand_tree.get_children(): self.stand_tree.delete(i)
        champ_txt = "No championship game found."
        
        for t in [team for team in self.teams if team.conference == conf]:
            w, l = 0, 0
            
            # Use .items() to iterate through the dictionary
            for week, data in t.schedule.items():
                if not data.get("is_champ", False):
                    if data["outcome"] == 'W': w += 1
                    elif data["outcome"] == 'L': l += 1
                else:
                    score_str = f"{data['team']['score']}-{data['opponent']['score']}"
                    champ_txt = f"Championship: {t.team_name} vs {data['opponent_name']} ({score_str})"
            
            pct = w / (w + l) if (w + l) > 0 else 0
            self.stand_tree.insert("", tk.END, values=(t.team_name, w, l, f"{pct:.3f}"))
            
        self.champ_info.config(text=champ_txt)
        self._apply_sort(self.stand_tree)

    def _on_rankings_double_click(self, event):
        item = self.rank_tree.identify_row(event.y)
        if item:
            name = self.rank_tree.item(item, 'values')[0] # Name is at index 0
            team = next(t for t in self.teams if t.team_name == name)
            self._open_rankings_schedule(team)

    def _on_sos_double_click(self, event):
        item = self.sos_tree.identify_row(event.y)
        if item:
            name = self.sos_tree.item(item, 'values')[0] # Name is at index 0
            team = next(t for t in self.teams if t.team_name == name)
            self._open_rankings_schedule(team)

    def _open_rankings_schedule(self, team):
        win = tk.Toplevel(self)
        win.title(f"Rankings Detail: {team.team_name}")
        win.geometry("850x450") # Wider to fit the new columns
        
        # 1. The Preseason Header requested
        pre_rank = team.ranking if team.ranking is not None else 200
        pre_elo = team.ELO if team.ELO is not None else 1300.0
        
        header = ttk.Label(win, text=f"Preseason Ranking/ELO: {pre_rank} | {pre_elo:.3f}", font=self.bold_font)
        header.pack(pady=(10, 5))

        # 2. Grid Container
        container = tk.Frame(win, background="black", highlightbackground="black", highlightthickness=1)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        cols = ("Week", "Opponent", "Outcome", "Score", "Delta ELO", "New ELO", "New Rank")
        tree = ttk.Treeview(container, columns=cols, show='headings')
        for c in cols: 
            tree.heading(c, text=c)
            # Make the data columns slightly smaller so everything fits well
            width = 120 if c in ["Opponent", "Score"] else 90
            tree.column(c, anchor=tk.CENTER, width=width)
        
        # 3. Populate Game Rows with Historical Data
        for week in sorted(team.schedule.keys()):
            data = team.schedule[week]
            score_str = f"{data['team']['score']}-{data['opponent']['score']}"
            
            # Fetch the stored history for this week
            history = team.weekly_history.get(week, {})
            delta_str = f"{history.get('delta', 0.0):+.3f}" if history else "-"
            new_elo_str = f"{history.get('new_elo', 0.0):.3f}" if history else "-"
            new_rank_str = str(history.get('new_rank', "-"))

            item = tree.insert("", tk.END, values=(week, data['opponent_name'], data['outcome'], score_str, delta_str, new_elo_str, new_rank_str))
            
            # W/L Color Coding
            if data['outcome'] == "W":
                tree.tag_configure('win', foreground='green')
                tree.item(item, tags=('win',))
            elif data['outcome'] == "L":
                tree.tag_configure('loss', foreground='red')
                tree.item(item, tags=('loss',))
                
        tree.pack(fill=tk.BOTH, expand=True)

def start_gui(teams):
    app = TeamViewer(teams)
    app.mainloop()