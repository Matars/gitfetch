use std::error::Error;
use std::io;
use std::io::Read;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::mpsc::{self, Receiver, Sender};
use std::thread;
use std::time::{Duration, Instant};
use std::{
    collections::{BTreeMap, HashSet},
    fs,
};

use crossterm::event::{self, Event, KeyCode, KeyEvent, KeyEventKind, KeyModifiers};
use crossterm::execute;
use crossterm::terminal::{
    disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
};
use portable_pty::{native_pty_system, CommandBuilder, MasterPty, PtySize};
use ratatui::backend::CrosstermBackend;
use ratatui::layout::{Alignment, Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Clear, List, ListItem, ListState, Paragraph};
use ratatui::Terminal;

#[derive(Clone, Debug)]
struct FileEntry {
    path: String,
    staged: bool,
    unstaged: bool,
    untracked: bool,
}

#[derive(Clone, Debug)]
enum Mode {
    Normal,
    CommitInput,
    WorktreeCommitPushInput,
    WorktreeCreateInput,
    WorktreeBranchConflictConfirm,
    QuitWithSessionsConfirm,
    AgentPopup,
}

#[derive(Clone, Debug, PartialEq, Eq)]
enum ViewMode {
    Changes,
    Worktrees,
}

struct App {
    branch: String,
    ahead: usize,
    behind: usize,
    files: Vec<FileEntry>,
    tree_items: Vec<TreeItem>,
    selected: usize,
    selected_overview: Option<FileOverview>,
    active_pane: ActivePane,
    overview_scroll: u16,
    status_line: String,
    mode: Mode,
    view_mode: ViewMode,
    commit_input: String,
    worktrees: Vec<WorktreeEntry>,
    selected_worktree: usize,
    worktree_focus: WorktreePane,
    show_panel_help: bool,
    new_worktree_branch: String,
    new_worktree_base: WorktreeCreateBase,
    pending_create_branch: String,
    confirm_delete_branch_yes: bool,
    worktree_commit_input: String,
    worktree_commit_path: Option<String>,
    confirm_quit_with_sessions_yes: bool,
    quit_now: bool,
    agent_sessions: BTreeMap<String, AgentSession>,
    agent_popup_path: Option<String>,
    terminal_popup_mode: TerminalPopupMode,
    agent_tx: Sender<AgentEvent>,
    agent_rx: Receiver<AgentEvent>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum TerminalPopupMode {
    Input,
    Control,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum AgentState {
    Launching,
    Running,
    Done,
    Failed,
}

struct AgentSession {
    state: AgentState,
    parser: vt100::Parser,
    master: Option<Box<dyn MasterPty + Send>>,
    writer: Option<Box<dyn Write + Send>>,
    child: Option<Box<dyn portable_pty::Child + Send>>,
    last_size: (u16, u16),
}

enum AgentEvent {
    Output { path: String, bytes: Vec<u8> },
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum WorktreePane {
    Canvas,
    Details,
    Actions,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum WorktreeCreateBase {
    Main,
    Selected,
    SelectedWithChanges,
}

#[derive(Clone, Debug, Default)]
struct WorktreeEntry {
    path: String,
    head: String,
    branch: String,
    bare: bool,
    detached: bool,
    locked: bool,
    prunable: bool,
    is_current: bool,
    dirty: bool,
    ahead: usize,
    behind: usize,
    parent_hint: Option<String>,
}

#[derive(Clone, Debug)]
struct TreeItem {
    path: String,
    label: String,
    kind: TreeKind,
    staged: bool,
    unstaged: bool,
    untracked: bool,
    added_lines: usize,
    removed_lines: usize,
}

#[derive(Clone, Debug, PartialEq, Eq)]
enum TreeKind {
    Folder,
    File,
}

#[derive(Clone, Copy, Debug, Default)]
struct PathStatus {
    staged: bool,
    unstaged: bool,
    untracked: bool,
}

#[derive(Clone, Copy, Debug, Default)]
struct PathDelta {
    added_lines: usize,
    removed_lines: usize,
}

#[derive(Clone, Debug, PartialEq, Eq)]
enum ActivePane {
    Files,
    Overview,
}

#[derive(Clone, Debug)]
struct FileOverview {
    file: String,
    state: String,
    added_lines: usize,
    removed_lines: usize,
    methods_added: Vec<String>,
    methods_modified: Vec<String>,
    methods_deleted: Vec<String>,
    traditional_diff: Vec<DiffPreviewLine>,
    use_traditional_overview: bool,
}

#[derive(Clone, Debug)]
struct DiffPreviewLine {
    kind: DiffPreviewKind,
    text: String,
}

#[derive(Clone, Debug)]
enum DiffPreviewKind {
    Added,
    Removed,
    Meta,
    Context,
}

impl App {
    fn new() -> Self {
        let (agent_tx, agent_rx) = mpsc::channel();
        Self {
            branch: "unknown".to_string(),
            ahead: 0,
            behind: 0,
            files: Vec::new(),
            tree_items: Vec::new(),
            selected: 0,
            selected_overview: None,
            active_pane: ActivePane::Files,
            overview_scroll: 0,
            status_line: "Ready".to_string(),
            mode: Mode::Normal,
            view_mode: ViewMode::Changes,
            commit_input: String::new(),
            worktrees: Vec::new(),
            selected_worktree: 0,
            worktree_focus: WorktreePane::Canvas,
            show_panel_help: false,
            new_worktree_branch: String::new(),
            new_worktree_base: WorktreeCreateBase::Selected,
            pending_create_branch: String::new(),
            confirm_delete_branch_yes: false,
            worktree_commit_input: String::new(),
            worktree_commit_path: None,
            confirm_quit_with_sessions_yes: false,
            quit_now: false,
            agent_sessions: BTreeMap::new(),
            agent_popup_path: None,
            terminal_popup_mode: TerminalPopupMode::Input,
            agent_tx,
            agent_rx,
        }
    }

    fn selected_item(&self) -> Option<&TreeItem> {
        self.tree_items.get(self.selected)
    }

    fn select_next(&mut self) {
        if self.tree_items.is_empty() {
            self.selected = 0;
        } else {
            self.selected = (self.selected + 1) % self.tree_items.len();
        }
    }

    fn select_prev(&mut self) {
        if self.tree_items.is_empty() {
            self.selected = 0;
        } else if self.selected == 0 {
            self.selected = self.tree_items.len() - 1;
        } else {
            self.selected -= 1;
        }
    }

    fn focus_left(&mut self) {
        self.active_pane = ActivePane::Files;
    }

    fn focus_right(&mut self) {
        self.active_pane = ActivePane::Overview;
    }

    fn selected_worktree(&self) -> Option<&WorktreeEntry> {
        self.worktrees.get(self.selected_worktree)
    }

    fn next_worktree_pane(&mut self) {
        self.worktree_focus = match self.worktree_focus {
            WorktreePane::Canvas => WorktreePane::Details,
            WorktreePane::Details => WorktreePane::Actions,
            WorktreePane::Actions => WorktreePane::Canvas,
        };
    }

    fn cycle_worktree_base_left(&mut self) {
        self.new_worktree_base = match self.new_worktree_base {
            WorktreeCreateBase::Main => WorktreeCreateBase::SelectedWithChanges,
            WorktreeCreateBase::Selected => WorktreeCreateBase::Main,
            WorktreeCreateBase::SelectedWithChanges => WorktreeCreateBase::Selected,
        };
    }

    fn cycle_worktree_base_right(&mut self) {
        self.new_worktree_base = match self.new_worktree_base {
            WorktreeCreateBase::Main => WorktreeCreateBase::Selected,
            WorktreeCreateBase::Selected => WorktreeCreateBase::SelectedWithChanges,
            WorktreeCreateBase::SelectedWithChanges => WorktreeCreateBase::Main,
        };
    }
}

struct TuiGuard;

impl Drop for TuiGuard {
    fn drop(&mut self) {
        let _ = disable_raw_mode();
        let mut stdout = io::stdout();
        let _ = execute!(stdout, LeaveAlternateScreen);
    }
}

fn main() -> Result<(), Box<dyn Error>> {
    enable_raw_mode()?;
    let _guard = TuiGuard;

    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen)?;

    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    let mut app = App::new();
    refresh_status(&mut app);

    let ui_tick_rate_fast = Duration::from_millis(16);
    let ui_tick_rate_normal = Duration::from_millis(33);
    let status_tick_rate = Duration::from_millis(1200);
    let mut last_ui_tick = Instant::now();
    let mut last_status_tick = Instant::now();
    let mut should_quit = false;

    while !should_quit {
        drain_agent_events(&mut app);
        refresh_agent_sessions(&mut app);

        // Resize terminal session to match actual popup dimensions
        if matches!(app.mode, Mode::AgentPopup) {
            if let Some(path) = app.agent_popup_path.clone() {
                let size = terminal.size()?;
                let frame_area = Rect::new(0, 0, size.width, size.height);
                let (rows, cols) = calc_terminal_popup_size(frame_area);
                resize_terminal_session(&mut app, &path, rows, cols);
            }
        }

        terminal.draw(|frame| draw_ui(frame, &app))?;

        let ui_tick_rate = if matches!(app.mode, Mode::AgentPopup) {
            ui_tick_rate_fast
        } else {
            ui_tick_rate_normal
        };
        let ui_timeout = ui_tick_rate.saturating_sub(last_ui_tick.elapsed());
        let status_timeout = status_tick_rate.saturating_sub(last_status_tick.elapsed());
        let timeout = if ui_timeout < status_timeout {
            ui_timeout
        } else {
            status_timeout
        };
        if event::poll(timeout)? {
            if let Event::Key(key) = event::read()? {
                if key.kind == KeyEventKind::Press {
                    if !matches!(app.mode, Mode::AgentPopup)
                        && key.modifiers.contains(KeyModifiers::CONTROL)
                        && key.code == KeyCode::Char('c')
                    {
                        should_quit = true;
                        continue;
                    }
                    match app.mode {
                        Mode::Normal => {
                            should_quit = handle_normal_mode_key(&mut app, key.code)?;
                        }
                        Mode::CommitInput => {
                            handle_commit_mode_key(&mut app, key.code)?;
                        }
                        Mode::WorktreeCommitPushInput => {
                            handle_worktree_commit_push_mode_key(&mut app, key.code)?;
                        }
                        Mode::WorktreeCreateInput => {
                            handle_worktree_create_mode_key(&mut app, key.code)?;
                        }
                        Mode::WorktreeBranchConflictConfirm => {
                            handle_branch_conflict_confirm_mode_key(&mut app, key.code)?;
                        }
                        Mode::QuitWithSessionsConfirm => {
                            handle_quit_with_sessions_mode_key(&mut app, key.code);
                        }
                        Mode::AgentPopup => {
                            handle_agent_popup_key(&mut app, key)?;
                        }
                    }

                    if app.quit_now {
                        should_quit = true;
                    }
                }
            }
        }

        if last_ui_tick.elapsed() >= ui_tick_rate {
            last_ui_tick = Instant::now();
        }

        let refresh_git = !matches!(app.mode, Mode::AgentPopup);
        if refresh_git && last_status_tick.elapsed() >= status_tick_rate {
            refresh_status(&mut app);
            last_status_tick = Instant::now();
        }
    }

    terminal.show_cursor()?;
    Ok(())
}

fn handle_normal_mode_key(app: &mut App, code: KeyCode) -> Result<bool, Box<dyn Error>> {
    if app.view_mode == ViewMode::Worktrees {
        return handle_worktree_mode_key(app, code);
    }

    match code {
        KeyCode::Char('q') => return Ok(request_quit(app)),
        KeyCode::Char('w') => {
            app.view_mode = ViewMode::Worktrees;
            app.worktree_focus = WorktreePane::Canvas;
            app.show_panel_help = false;
            app.status_line = "Switched to worktree navigator".to_string();
            refresh_worktrees(app);
        }
        KeyCode::Left | KeyCode::Char('h') => app.focus_left(),
        KeyCode::Right | KeyCode::Char('l') => app.focus_right(),
        KeyCode::Down | KeyCode::Char('j') => match app.active_pane {
            ActivePane::Files => {
                app.select_next();
                app.overview_scroll = 0;
                refresh_selected_overview(app);
            }
            ActivePane::Overview => {
                app.overview_scroll = app.overview_scroll.saturating_add(1);
            }
        },
        KeyCode::Up | KeyCode::Char('k') => match app.active_pane {
            ActivePane::Files => {
                app.select_prev();
                app.overview_scroll = 0;
                refresh_selected_overview(app);
            }
            ActivePane::Overview => {
                app.overview_scroll = app.overview_scroll.saturating_sub(1);
            }
        },
        KeyCode::Char('r') => refresh_status(app),
        KeyCode::Enter | KeyCode::Char(' ') => {
            toggle_stage(app)?;
            refresh_status(app);
        }
        KeyCode::Char('c') => {
            app.mode = Mode::CommitInput;
            app.commit_input.clear();
            app.status_line = "Commit mode: type a message and press Enter".to_string();
        }
        KeyCode::Char('p') => {
            let output = push_with_upstream()?;
            app.status_line = output;
            refresh_status(app);
        }
        KeyCode::Char('s') => {
            app.status_line = run_git(&["stash", "push", "--include-untracked"])?;
            refresh_status(app);
        }
        KeyCode::Char('S') => {
            app.status_line = run_git(&["stash", "pop"])?;
            refresh_status(app);
        }
        _ => {}
    }

    Ok(false)
}

fn handle_worktree_mode_key(app: &mut App, code: KeyCode) -> Result<bool, Box<dyn Error>> {
    match code {
        KeyCode::Char('q') => return Ok(request_quit(app)),
        KeyCode::Char('w') => {
            app.view_mode = ViewMode::Changes;
            app.show_panel_help = false;
            app.status_line = "Switched to changed files view".to_string();
        }
        KeyCode::Tab => {
            app.next_worktree_pane();
            app.show_panel_help = false;
        }
        KeyCode::Char('?') => {
            app.show_panel_help = !app.show_panel_help;
        }
        KeyCode::Left => move_worktree_selection(app, NavDirection::Left),
        KeyCode::Right => move_worktree_selection(app, NavDirection::Right),
        KeyCode::Up => move_worktree_selection(app, NavDirection::Up),
        KeyCode::Down => move_worktree_selection(app, NavDirection::Down),
        KeyCode::Char('h') => move_worktree_level_siblings(app, false),
        KeyCode::Char('l') => move_worktree_level_siblings(app, true),
        KeyCode::Char('j') => move_worktree_level_vertical(app, false),
        KeyCode::Char('k') => move_worktree_level_vertical(app, true),
        KeyCode::Char('r') => {
            refresh_worktrees(app);
            app.status_line = "Refreshed worktree list".to_string();
        }
        KeyCode::Char('a') => {
            app.mode = Mode::WorktreeCreateInput;
            app.new_worktree_branch.clear();
            app.new_worktree_base = WorktreeCreateBase::Selected;
            app.status_line =
                "Create worktree: choose base with ←/→, then type branch name".to_string();
        }
        KeyCode::Char('o') => {
            open_terminal_popup_for_selected_worktree(app)?;
        }
        KeyCode::Char('z') => {
            open_terminal_popup_for_selected_worktree(app)?;
        }
        KeyCode::Char('f') => {
            if let Some(selected) = app.selected_worktree() {
                let output = run_git(&["-C", selected.path.as_str(), "fetch", "--all", "--prune"])?;
                app.status_line = output;
                refresh_worktrees(app);
            }
        }
        KeyCode::Char('p') => {
            if let Some(selected) = app.selected_worktree() {
                let output = run_git(&["-C", selected.path.as_str(), "pull", "--ff-only"])?;
                app.status_line = output;
                refresh_worktrees(app);
            }
        }
        KeyCode::Char('x') => {
            app.status_line = run_git(&["worktree", "prune"])?;
            refresh_worktrees(app);
        }
        KeyCode::Char('d') => {
            app.status_line = remove_selected_worktree(app)?;
            refresh_worktrees(app);
            refresh_status(app);
        }
        KeyCode::Char('m') => {
            app.status_line = merge_selected_into_parent(app)?;
            refresh_worktrees(app);
            refresh_status(app);
        }
        KeyCode::Char('P') => {
            if let Some(path) = app.selected_worktree().map(|wt| wt.path.clone()) {
                app.mode = Mode::WorktreeCommitPushInput;
                app.worktree_commit_input.clear();
                app.worktree_commit_path = Some(path);
                app.status_line =
                    "Worktree push mode: commit message, Enter to add/commit/push".to_string();
            }
        }
        KeyCode::Char('u') => {
            app.status_line = update_connected_parent(app)?;
            refresh_worktrees(app);
            refresh_status(app);
        }
        _ => {}
    }

    Ok(false)
}

fn open_terminal_popup_for_selected_worktree(app: &mut App) -> Result<(), Box<dyn Error>> {
    if let Some(path) = app.selected_worktree().map(|wt| wt.path.clone()) {
        app.agent_popup_path = Some(path.clone());
        app.mode = Mode::AgentPopup;
        app.terminal_popup_mode = TerminalPopupMode::Input;
        if !has_live_terminal_session(app, path.as_str()) {
            launch_shell_session(app, path.as_str())?;
        } else {
            app.status_line = "Reopened terminal session".to_string();
        }
    }
    Ok(())
}

fn request_quit(app: &mut App) -> bool {
    if live_terminal_session_count(app) == 0 {
        return true;
    }

    app.mode = Mode::QuitWithSessionsConfirm;
    app.confirm_quit_with_sessions_yes = false;
    app.status_line = "Active terminal sessions detected".to_string();
    false
}

fn live_terminal_session_count(app: &App) -> usize {
    app.agent_sessions
        .values()
        .filter(|session| session.child.is_some())
        .count()
}

fn handle_quit_with_sessions_mode_key(app: &mut App, code: KeyCode) {
    match code {
        KeyCode::Esc => {
            app.mode = Mode::Normal;
            app.confirm_quit_with_sessions_yes = false;
            app.status_line = "Quit cancelled".to_string();
        }
        KeyCode::Left | KeyCode::Right | KeyCode::Tab => {
            app.confirm_quit_with_sessions_yes = !app.confirm_quit_with_sessions_yes;
        }
        KeyCode::Char('y') => app.confirm_quit_with_sessions_yes = true,
        KeyCode::Char('n') => app.confirm_quit_with_sessions_yes = false,
        KeyCode::Enter => {
            if app.confirm_quit_with_sessions_yes {
                app.quit_now = true;
            } else {
                app.mode = Mode::Normal;
                app.status_line = "Quit cancelled".to_string();
            }
        }
        _ => {}
    }
}

fn handle_worktree_create_mode_key(app: &mut App, code: KeyCode) -> Result<(), Box<dyn Error>> {
    match code {
        KeyCode::Esc => {
            app.mode = Mode::Normal;
            app.status_line = "Create worktree cancelled".to_string();
        }
        KeyCode::Left => {
            app.cycle_worktree_base_left();
        }
        KeyCode::Right => {
            app.cycle_worktree_base_right();
        }
        KeyCode::Enter => {
            let branch = app.new_worktree_branch.trim();
            if branch.is_empty() {
                app.status_line = "Branch name is required".to_string();
            } else {
                let root = create_root_for_app(app);
                if branch_exists(root.as_str(), branch) {
                    app.pending_create_branch = branch.to_string();
                    app.confirm_delete_branch_yes = false;
                    app.mode = Mode::WorktreeBranchConflictConfirm;
                    app.status_line = format!(
                        "Branch '{}' already exists. Confirm delete and recreate.",
                        branch
                    );
                    return Ok(());
                }

                app.status_line = create_worktree(app, branch)?;
                refresh_worktrees(app);
                refresh_status(app);
            }
            app.mode = Mode::Normal;
            app.new_worktree_branch.clear();
        }
        KeyCode::Backspace => {
            app.new_worktree_branch.pop();
        }
        KeyCode::Char(c) => {
            app.new_worktree_branch.push(c);
        }
        _ => {}
    }

    Ok(())
}

fn handle_branch_conflict_confirm_mode_key(
    app: &mut App,
    code: KeyCode,
) -> Result<(), Box<dyn Error>> {
    match code {
        KeyCode::Esc => {
            app.mode = Mode::Normal;
            app.confirm_delete_branch_yes = false;
            app.pending_create_branch.clear();
            app.status_line = "Create worktree cancelled".to_string();
        }
        KeyCode::Left | KeyCode::Right | KeyCode::Tab => {
            app.confirm_delete_branch_yes = !app.confirm_delete_branch_yes;
        }
        KeyCode::Char('y') => app.confirm_delete_branch_yes = true,
        KeyCode::Char('n') => app.confirm_delete_branch_yes = false,
        KeyCode::Enter => {
            if app.confirm_delete_branch_yes {
                let branch = app.pending_create_branch.clone();
                let root = create_root_for_app(app);
                app.status_line =
                    delete_branch_and_create_worktree(app, root.as_str(), branch.as_str())?;
                refresh_worktrees(app);
                refresh_status(app);
            } else {
                app.status_line = "Create worktree cancelled (kept existing branch)".to_string();
            }

            app.mode = Mode::Normal;
            app.confirm_delete_branch_yes = false;
            app.pending_create_branch.clear();
            app.new_worktree_branch.clear();
        }
        _ => {}
    }

    Ok(())
}

fn handle_agent_popup_key(app: &mut App, key: KeyEvent) -> Result<(), Box<dyn Error>> {
    let code = key.code;
    let Some(path) = app.agent_popup_path.clone() else {
        app.mode = Mode::Normal;
        return Ok(());
    };

    if !has_live_terminal_session(app, path.as_str()) {
        launch_shell_session(app, path.as_str())?;
    }

    if key.modifiers.contains(KeyModifiers::CONTROL) && matches!(code, KeyCode::Char('g')) {
        app.terminal_popup_mode = match app.terminal_popup_mode {
            TerminalPopupMode::Input => TerminalPopupMode::Control,
            TerminalPopupMode::Control => TerminalPopupMode::Input,
        };
        return Ok(());
    }

    if app.terminal_popup_mode == TerminalPopupMode::Control {
        match code {
            KeyCode::Esc => {
                app.mode = Mode::Normal;
                app.agent_popup_path = None;
                app.status_line = "Terminal session moved to background".to_string();
            }
            KeyCode::Char('q') => {
                terminate_terminal_session(app, path.as_str());
                app.mode = Mode::Normal;
                app.agent_popup_path = None;
                app.status_line = "Terminal session closed".to_string();
            }
            KeyCode::Char('r') => {
                app.agent_sessions.remove(path.as_str());
                launch_shell_session(app, path.as_str())?;
                app.status_line = "Terminal restarted".to_string();
            }
            KeyCode::Char('i') => {
                app.terminal_popup_mode = TerminalPopupMode::Input;
            }
            _ => {}
        }
        return Ok(());
    }

    match code {
        KeyCode::Tab => {
            write_to_agent(app, path.as_str(), "\t")?;
        }
        KeyCode::Left => {
            write_to_agent(app, path.as_str(), "\x1b[D")?;
        }
        KeyCode::Right => {
            write_to_agent(app, path.as_str(), "\x1b[C")?;
        }
        KeyCode::Up => {
            write_to_agent(app, path.as_str(), "\x1b[A")?;
        }
        KeyCode::Down => {
            write_to_agent(app, path.as_str(), "\x1b[B")?;
        }
        KeyCode::Home => {
            write_to_agent(app, path.as_str(), "\x1b[H")?;
        }
        KeyCode::End => {
            write_to_agent(app, path.as_str(), "\x1b[F")?;
        }
        KeyCode::PageUp => {
            write_to_agent(app, path.as_str(), "\x1b[5~")?;
        }
        KeyCode::PageDown => {
            write_to_agent(app, path.as_str(), "\x1b[6~")?;
        }
        KeyCode::Delete => {
            write_to_agent(app, path.as_str(), "\x1b[3~")?;
        }
        KeyCode::Backspace => {
            write_to_agent(app, path.as_str(), "\x7f")?;
        }
        KeyCode::Enter => {
            write_to_agent(app, path.as_str(), "\r")?;
        }
        KeyCode::Char(c) => {
            if key.modifiers.contains(KeyModifiers::CONTROL) {
                if let Some(seq) = control_seq(c) {
                    write_to_agent(app, path.as_str(), seq)?;
                }
            } else {
                let mut s = String::new();
                s.push(c);
                write_to_agent(app, path.as_str(), s.as_str())?;
            }
        }
        _ => {}
    }

    Ok(())
}

fn terminate_terminal_session(app: &mut App, path: &str) {
    if let Some(mut session) = app.agent_sessions.remove(path) {
        if let Some(mut child) = session.child.take() {
            let _ = child.kill();
        }
    }
}

fn control_seq(c: char) -> Option<&'static str> {
    match c.to_ascii_lowercase() {
        'a' => Some("\x01"),
        'b' => Some("\x02"),
        'c' => Some("\x03"),
        'd' => Some("\x04"),
        'e' => Some("\x05"),
        'f' => Some("\x06"),
        'g' => Some("\x07"),
        'h' => Some("\x08"),
        'i' => Some("\x09"),
        'j' => Some("\x0A"),
        'k' => Some("\x0B"),
        'l' => Some("\x0C"),
        'm' => Some("\x0D"),
        'n' => Some("\x0E"),
        'o' => Some("\x0F"),
        'p' => Some("\x10"),
        'q' => Some("\x11"),
        'r' => Some("\x12"),
        's' => Some("\x13"),
        't' => Some("\x14"),
        'u' => Some("\x15"),
        'v' => Some("\x16"),
        'w' => Some("\x17"),
        'x' => Some("\x18"),
        'y' => Some("\x19"),
        'z' => Some("\x1A"),
        _ => None,
    }
}

fn has_live_terminal_session(app: &App, path: &str) -> bool {
    app.agent_sessions
        .get(path)
        .map(|session| session.child.is_some() && session.writer.is_some())
        .unwrap_or(false)
}

fn launch_shell_session(app: &mut App, path: &str) -> Result<(), Box<dyn Error>> {
    const TERM_ROWS: u16 = 44;
    const TERM_COLS: u16 = 150;

    let pty_system = native_pty_system();
    let pair = pty_system.openpty(PtySize {
        rows: TERM_ROWS,
        cols: TERM_COLS,
        pixel_width: 0,
        pixel_height: 0,
    })?;

    let shell = std::env::var("SHELL").unwrap_or_else(|_| "zsh".to_string());
    let mut cmd = CommandBuilder::new(shell.as_str());
    cmd.arg("-i");
    cmd.arg("-l");
    cmd.cwd(path);
    let child = pair.slave.spawn_command(cmd)?;

    let tx = app.agent_tx.clone();
    let mut reader = pair.master.try_clone_reader()?;
    let writer = pair.master.take_writer()?;
    let output_path = path.to_string();
    thread::spawn(move || {
        let mut buf = [0u8; 1024];
        loop {
            match reader.read(&mut buf) {
                Ok(0) => break,
                Ok(n) => {
                    let _ = tx.send(AgentEvent::Output {
                        path: output_path.clone(),
                        bytes: buf[..n].to_vec(),
                    });
                }
                Err(_) => break,
            }
        }
    });

    let session = AgentSession {
        state: AgentState::Launching,
        parser: vt100::Parser::new(TERM_ROWS, TERM_COLS, 2000),
        master: Some(pair.master),
        writer: Some(writer),
        child: Some(child),
        last_size: (TERM_ROWS, TERM_COLS),
    };

    app.agent_sessions.insert(path.to_string(), session);
    if let Some(active) = app.agent_sessions.get_mut(path) {
        active
            .parser
            .process(b"[terminal attached - type commands and press Enter]\r\n");
    }
    app.status_line = format!("Shell started in popup for {}", path);
    Ok(())
}

fn resize_terminal_session(app: &mut App, path: &str, rows: u16, cols: u16) {
    if let Some(session) = app.agent_sessions.get_mut(path) {
        // Only resize if size actually changed
        if session.last_size == (rows, cols) {
            return;
        }
        // Resize the PTY
        if let Some(master) = session.master.as_ref() {
            let _ = master.resize(PtySize {
                rows,
                cols,
                pixel_width: 0,
                pixel_height: 0,
            });
        }
        // Resize the vt100 parser to match
        session.parser.set_size(rows, cols);
        session.last_size = (rows, cols);
    }
}

/// Calculate terminal popup dimensions based on frame size
fn calc_terminal_popup_size(frame_area: Rect) -> (u16, u16) {
    let popup = terminal_popup_rect(frame_area);
    let inner = Layout::default()
        .direction(Direction::Vertical)
        .margin(1)
        .constraints([
            Constraint::Length(1),
            Constraint::Length(3),
            Constraint::Min(8),
            Constraint::Length(1),
        ])
        .split(popup);
    // Terminal area is inner[2], minus borders
    let rows = inner[2].height.saturating_sub(2);
    let cols = inner[2].width.saturating_sub(2);
    (rows, cols)
}

fn write_to_agent(app: &mut App, path: &str, text: &str) -> Result<(), Box<dyn Error>> {
    if let Some(session) = app.agent_sessions.get_mut(path) {
        if let Some(writer) = session.writer.as_mut() {
            writer.write_all(text.as_bytes())?;
            writer.flush()?;
        }
    }
    Ok(())
}

fn drain_agent_events(app: &mut App) {
    while let Ok(event) = app.agent_rx.try_recv() {
        match event {
            AgentEvent::Output { path, bytes } => {
                if let Some(session) = app.agent_sessions.get_mut(path.as_str()) {
                    session.state = AgentState::Running;
                    session.parser.process(bytes.as_slice());
                }
            }
        }
    }
}

fn refresh_agent_sessions(app: &mut App) {
    for session in app.agent_sessions.values_mut() {
        if let Some(child) = session.child.as_mut() {
            if let Ok(Some(status)) = child.try_wait() {
                if status.success() {
                    session.state = AgentState::Done;
                    session
                        .parser
                        .process(b"\r\n[terminal exited successfully]\r\n");
                } else {
                    session.state = AgentState::Failed;
                    let line = format!("\r\n[terminal exited: {}]\r\n", status);
                    session.parser.process(line.as_bytes());
                }
                session.child = None;
                session.writer = None;
            }
        }
    }
}

fn handle_commit_mode_key(app: &mut App, code: KeyCode) -> Result<(), Box<dyn Error>> {
    match code {
        KeyCode::Esc => {
            app.mode = Mode::Normal;
            app.status_line = "Commit cancelled".to_string();
        }
        KeyCode::Enter => {
            let message = app.commit_input.trim();
            if message.is_empty() {
                app.status_line = "Commit message is empty".to_string();
            } else {
                let output = run_git(&["commit", "-m", message])?;
                app.status_line = output;
                refresh_status(app);
            }
            app.mode = Mode::Normal;
            app.commit_input.clear();
        }
        KeyCode::Backspace => {
            app.commit_input.pop();
        }
        KeyCode::Char(c) => {
            app.commit_input.push(c);
        }
        _ => {}
    }

    Ok(())
}

fn handle_worktree_commit_push_mode_key(
    app: &mut App,
    code: KeyCode,
) -> Result<(), Box<dyn Error>> {
    match code {
        KeyCode::Esc => {
            app.mode = Mode::Normal;
            app.worktree_commit_input.clear();
            app.worktree_commit_path = None;
            app.status_line = "Worktree commit/push cancelled".to_string();
        }
        KeyCode::Enter => {
            let message = app.worktree_commit_input.trim().to_string();
            let Some(path) = app.worktree_commit_path.clone() else {
                app.status_line = "No worktree selected for commit/push".to_string();
                app.mode = Mode::Normal;
                return Ok(());
            };

            if message.is_empty() {
                app.status_line = "Commit message is empty".to_string();
            } else {
                app.status_line = commit_and_push_worktree(path.as_str(), message.as_str())?;
                refresh_worktrees(app);
                refresh_status(app);
            }

            app.mode = Mode::Normal;
            app.worktree_commit_input.clear();
            app.worktree_commit_path = None;
        }
        KeyCode::Backspace => {
            app.worktree_commit_input.pop();
        }
        KeyCode::Char(c) => {
            app.worktree_commit_input.push(c);
        }
        _ => {}
    }

    Ok(())
}

fn refresh_status(app: &mut App) {
    let output = match run_git(&["status", "--porcelain=1", "-b", "-uall"]) {
        Ok(text) => text,
        Err(err) => {
            app.status_line = err.to_string();
            return;
        }
    };

    let mut lines = output.lines();
    if let Some(head) = lines.next() {
        parse_branch_line(app, head);
    }

    let mut files = Vec::new();
    for line in lines {
        if line.len() < 4 {
            continue;
        }

        let x = line.chars().next().unwrap_or(' ');
        let y = line.chars().nth(1).unwrap_or(' ');
        let path = line[3..].trim().to_string();

        if should_hide_internal_worktree_path(path.as_str()) {
            continue;
        }

        files.push(FileEntry {
            path,
            staged: x != ' ' && x != '?',
            unstaged: y != ' ',
            untracked: x == '?' && y == '?',
        });
    }

    app.files = files;
    app.tree_items = build_tree_items(&app.files);

    if app.tree_items.is_empty() {
        app.selected = 0;
    } else if app.selected >= app.tree_items.len() {
        app.selected = app.tree_items.len() - 1;
    }

    let max_scroll = max_overview_scroll(app);
    if app.overview_scroll > max_scroll {
        app.overview_scroll = max_scroll;
    }

    refresh_selected_overview(app);
    refresh_worktrees(app);
}

fn refresh_worktrees(app: &mut App) {
    let output = match git_output(&["worktree", "list", "--porcelain"]) {
        Some(text) => text,
        None => {
            app.worktrees.clear();
            app.selected_worktree = 0;
            return;
        }
    };

    let current_path = std::env::current_dir()
        .ok()
        .map(|path| normalize_path(path.to_string_lossy().as_ref()));
    let root = create_root_for_app(app);
    let parent_hints = load_parent_hint_map(root.as_str());

    let mut entries: Vec<WorktreeEntry> = Vec::new();
    let mut current = WorktreeEntry::default();
    let mut in_block = false;

    for line in output.lines() {
        if line.trim().is_empty() {
            if in_block {
                hydrate_worktree_runtime_state(
                    &mut current,
                    current_path.as_deref(),
                    &parent_hints,
                );
                entries.push(current.clone());
                current = WorktreeEntry::default();
                in_block = false;
            }
            continue;
        }

        if let Some(path) = line.strip_prefix("worktree ") {
            if in_block {
                hydrate_worktree_runtime_state(
                    &mut current,
                    current_path.as_deref(),
                    &parent_hints,
                );
                entries.push(current.clone());
                current = WorktreeEntry::default();
            }
            current.path = path.trim().to_string();
            in_block = true;
            continue;
        }

        if let Some(head) = line.strip_prefix("HEAD ") {
            current.head = head.trim().to_string();
            continue;
        }

        if let Some(branch) = line.strip_prefix("branch ") {
            current.branch = branch
                .trim()
                .strip_prefix("refs/heads/")
                .unwrap_or(branch.trim())
                .to_string();
            continue;
        }

        if line == "detached" {
            current.detached = true;
            if current.branch.is_empty() {
                current.branch = "detached".to_string();
            }
            continue;
        }

        if line == "bare" {
            current.bare = true;
            continue;
        }

        if line.starts_with("locked") {
            current.locked = true;
            continue;
        }

        if line.starts_with("prunable") {
            current.prunable = true;
            continue;
        }
    }

    if in_block {
        hydrate_worktree_runtime_state(&mut current, current_path.as_deref(), &parent_hints);
        entries.push(current);
    }

    entries.sort_by(|a, b| {
        b.is_current
            .cmp(&a.is_current)
            .then_with(|| a.branch.cmp(&b.branch))
            .then_with(|| a.path.cmp(&b.path))
    });

    app.worktrees = entries;
    if app.worktrees.is_empty() {
        app.selected_worktree = 0;
    } else if app.selected_worktree >= app.worktrees.len() {
        app.selected_worktree = app.worktrees.len() - 1;
    }
}

fn hydrate_worktree_runtime_state(
    entry: &mut WorktreeEntry,
    current_path: Option<&str>,
    parent_hints: &BTreeMap<String, String>,
) {
    let normalized = normalize_path(entry.path.as_str());
    entry.is_current = current_path
        .map(|cwd| cwd == normalized.as_str())
        .unwrap_or(false);

    if entry.branch.is_empty() {
        entry.branch = "detached".to_string();
    }

    let (dirty, ahead, behind) = worktree_branch_state(entry.path.as_str());
    entry.dirty = dirty;
    entry.ahead = ahead;
    entry.behind = behind;
    entry.parent_hint = parent_hints.get(entry.branch.as_str()).cloned();
}

fn worktree_branch_state(path: &str) -> (bool, usize, usize) {
    let output = match Command::new("git")
        .args(["-C", path, "status", "--porcelain=1", "-b", "-uall"])
        .output()
    {
        Ok(out) if out.status.success() => {
            sanitize_for_tui(String::from_utf8_lossy(&out.stdout).as_ref())
        }
        _ => return (false, 0, 0),
    };

    let mut lines = output.lines();
    let mut ahead = 0usize;
    let mut behind = 0usize;
    if let Some(head) = lines.next() {
        let (_, parsed_ahead, parsed_behind) = parse_branch_snapshot(head);
        ahead = parsed_ahead;
        behind = parsed_behind;
    }
    let dirty = lines.any(|line| status_line_counts_as_dirty(line));
    (dirty, ahead, behind)
}

fn status_line_counts_as_dirty(line: &str) -> bool {
    let trimmed = line.trim();
    if trimmed.is_empty() {
        return false;
    }

    if let Some(path) = trimmed.strip_prefix("?? ") {
        return !should_hide_internal_worktree_path(path.trim());
    }

    if let Some(path) = trimmed.strip_prefix("!! ") {
        return !should_hide_internal_worktree_path(path.trim());
    }

    true
}

fn parse_branch_snapshot(line: &str) -> (String, usize, usize) {
    let mut ahead = 0usize;
    let mut behind = 0usize;

    let stripped = line.strip_prefix("## ").unwrap_or(line);
    let branch = if let Some((name, rest)) = stripped.split_once("...") {
        if let Some(start) = rest.find('[') {
            if let Some(end) = rest[start + 1..].find(']') {
                let info = &rest[start + 1..start + 1 + end];
                for token in info.split(',').map(|part| part.trim()) {
                    if let Some(v) = token.strip_prefix("ahead ") {
                        ahead = v.parse::<usize>().unwrap_or(0);
                    }
                    if let Some(v) = token.strip_prefix("behind ") {
                        behind = v.parse::<usize>().unwrap_or(0);
                    }
                }
            }
        }
        name.trim().to_string()
    } else {
        stripped.trim().to_string()
    };

    (branch, ahead, behind)
}

fn normalize_path(path: &str) -> String {
    fs::canonicalize(Path::new(path))
        .unwrap_or_else(|_| Path::new(path).to_path_buf())
        .to_string_lossy()
        .to_string()
}

fn remove_selected_worktree(app: &App) -> Result<String, Box<dyn Error>> {
    let Some(selected) = app.selected_worktree() else {
        return Ok("No worktree selected".to_string());
    };

    if selected.is_current {
        return Ok("Refusing to remove current worktree".to_string());
    }

    if selected.dirty {
        return Ok("Refusing to remove dirty worktree (clean it first)".to_string());
    }

    run_git(&["worktree", "remove", selected.path.as_str()])
}

fn merge_selected_into_parent(app: &App) -> Result<String, Box<dyn Error>> {
    if app.selected_worktree >= app.worktrees.len() {
        return Ok("No worktree selected".to_string());
    }

    let selected = app.worktrees[app.selected_worktree].clone();
    if selected.detached || selected.branch.is_empty() {
        return Ok("Selected worktree is detached; merge requires a branch".to_string());
    }

    let Some(parent_idx) = connected_parent_index(app) else {
        return Ok("No connected parent node found for selected worktree".to_string());
    };
    let parent = app.worktrees[parent_idx].clone();

    if parent.detached || parent.branch.is_empty() {
        return Ok("Parent node is detached; cannot merge into detached HEAD".to_string());
    }
    if parent.branch == selected.branch {
        return Ok("Selected and parent are the same branch; nothing to merge".to_string());
    }

    let before_head = git_output(&["-C", parent.path.as_str(), "rev-parse", "HEAD"])
        .map(|s| s.trim().to_string())
        .unwrap_or_default();

    // Use an explicit commit/ref target to avoid ambiguous names like "stash"
    // resolving to refs/stash instead of refs/heads/stash.
    let merge_target = if !selected.head.is_empty() {
        selected.head.clone()
    } else {
        format!("refs/heads/{}", selected.branch)
    };

    let merge = Command::new("git")
        .args([
            "-C",
            parent.path.as_str(),
            "merge",
            "--no-edit",
            merge_target.as_str(),
        ])
        .output()?;

    let stdout = sanitize_for_tui(String::from_utf8_lossy(&merge.stdout).as_ref())
        .trim()
        .to_string();
    let stderr = sanitize_for_tui(String::from_utf8_lossy(&merge.stderr).as_ref())
        .trim()
        .to_string();

    if !merge.status.success() {
        let reason = if !stderr.is_empty() {
            stderr
        } else if !stdout.is_empty() {
            stdout
        } else {
            "merge failed".to_string()
        };
        return Ok(format!(
            "Merge '{}' -> '{}' failed:\n{}",
            selected.branch,
            parent.branch,
            sanitize_for_tui(reason.as_str())
        ));
    }

    let after_head = git_output(&["-C", parent.path.as_str(), "rev-parse", "HEAD"])
        .map(|s| s.trim().to_string())
        .unwrap_or_default();

    let details = if !stdout.is_empty() {
        single_line(stdout.as_str())
    } else if !stderr.is_empty() {
        single_line(stderr.as_str())
    } else {
        "ok".to_string()
    };

    if !before_head.is_empty() && before_head == after_head {
        Ok(format!(
            "No new merge for '{}' -> '{}' ({}) - {}",
            selected.branch, parent.branch, parent.path, details
        ))
    } else {
        Ok(format!(
            "Merged '{}' into '{}' ({}) [{} -> {}] - {}",
            selected.branch,
            parent.branch,
            parent.path,
            truncate_text(before_head.as_str(), 8),
            truncate_text(after_head.as_str(), 8),
            details
        ))
    }
}

fn update_connected_parent(app: &App) -> Result<String, Box<dyn Error>> {
    let Some(parent_idx) = connected_parent_index(app) else {
        return Ok("No connected parent node found for selected worktree".to_string());
    };
    let parent = app.worktrees[parent_idx].clone();

    if parent.detached || parent.branch.is_empty() {
        return Ok("Parent node is detached; cannot pull updates".to_string());
    }

    if parent.dirty {
        return Ok(format!(
            "Parent '{}' is dirty; commit/stash there before pull",
            parent.branch
        ));
    }

    let fetch = run_git(&["-C", parent.path.as_str(), "fetch", "--all", "--prune"])?;
    let pull = run_git(&["-C", parent.path.as_str(), "pull", "--ff-only"])?;

    Ok(format!(
        "Updated parent '{}' - {} | {}",
        parent.branch,
        single_line(fetch.as_str()),
        single_line(pull.as_str())
    ))
}

fn connected_parent_index(app: &App) -> Option<usize> {
    if app.selected_worktree >= app.worktrees.len() {
        return None;
    }

    let root_branch = current_session_branch(app);
    let parents = worktree_parent_map(&app.worktrees, root_branch.as_str());
    if let Some(parent_idx) = parents.get(app.selected_worktree).and_then(|v| *v) {
        return Some(parent_idx);
    }

    app.worktrees.iter().enumerate().find_map(|(idx, wt)| {
        if idx == app.selected_worktree {
            return None;
        }
        if !wt.detached && wt.branch == root_branch {
            Some(idx)
        } else {
            None
        }
    })
}

#[derive(Clone, Copy)]
enum NavDirection {
    Left,
    Right,
    Up,
    Down,
}

fn move_worktree_selection(app: &mut App, direction: NavDirection) {
    if app.worktrees.len() < 2 || app.selected_worktree >= app.worktrees.len() {
        return;
    }

    let root_branch = current_session_branch(app);
    let parents = worktree_parent_map(&app.worktrees, root_branch.as_str());
    let depths = graph_depths(&parents);
    let points = graph_layout(&parents);
    let (cx, cy) = points[app.selected_worktree];
    let mut best_idx: Option<usize> = None;
    let mut best_score = f32::MAX;

    for (idx, (x, y)) in points.iter().enumerate() {
        if idx == app.selected_worktree {
            continue;
        }

        let dx = *x - cx;
        let dy = *y - cy;
        let in_front = match direction {
            NavDirection::Left => dx < -0.15,
            NavDirection::Right => dx > 0.15,
            NavDirection::Up => dy < -0.15,
            NavDirection::Down => dy > 0.15,
        };
        if !in_front {
            continue;
        }

        let directional_penalty = match direction {
            NavDirection::Left | NavDirection::Right => dy.abs() * 1.7,
            NavDirection::Up | NavDirection::Down => dx.abs() * 1.7,
        };
        let score = dx.abs() + dy.abs() + directional_penalty;
        if score < best_score {
            best_score = score;
            best_idx = Some(idx);
        }
    }

    if best_idx.is_none() {
        let current = app.selected_worktree;
        let current_depth = depths[current];
        let max_depth = depths.iter().copied().max().unwrap_or(0);
        let mut rows: BTreeMap<usize, Vec<usize>> = BTreeMap::new();
        for (idx, depth) in depths.iter().enumerate() {
            rows.entry(*depth).or_default().push(idx);
        }
        for nodes in rows.values_mut() {
            nodes.sort_by(|a, b| points[*a].0.total_cmp(&points[*b].0));
        }

        let current_pos = rows
            .get(&current_depth)
            .and_then(|nodes| nodes.iter().position(|idx| *idx == current))
            .unwrap_or(0);

        let next_nonempty_depth = |order: Vec<usize>, rows: &BTreeMap<usize, Vec<usize>>| {
            order
                .into_iter()
                .find(|depth| rows.get(depth).map(|n| !n.is_empty()).unwrap_or(false))
        };

        best_idx = match direction {
            NavDirection::Right => {
                let next_on_row = rows
                    .get(&current_depth)
                    .and_then(|nodes| nodes.get(current_pos + 1))
                    .copied();
                next_on_row.or_else(|| {
                    let order: Vec<usize> = ((current_depth + 1)..=max_depth)
                        .chain(0..=current_depth)
                        .collect();
                    next_nonempty_depth(order, &rows)
                        .and_then(|depth| rows.get(&depth))
                        .and_then(|nodes| nodes.last())
                        .copied()
                })
            }
            NavDirection::Left => {
                let prev_on_row = rows
                    .get(&current_depth)
                    .and_then(|nodes| current_pos.checked_sub(1).and_then(|pos| nodes.get(pos)))
                    .copied();
                prev_on_row.or_else(|| {
                    let order: Vec<usize> = (0..current_depth)
                        .rev()
                        .chain((current_depth..=max_depth).rev())
                        .collect();
                    next_nonempty_depth(order, &rows)
                        .and_then(|depth| rows.get(&depth))
                        .and_then(|nodes| nodes.first())
                        .copied()
                })
            }
            NavDirection::Down => {
                let order: Vec<usize> = ((current_depth + 1)..=max_depth)
                    .chain(0..=current_depth)
                    .collect();
                next_nonempty_depth(order, &rows)
                    .and_then(|depth| rows.get(&depth))
                    .and_then(|nodes| {
                        nodes.iter().copied().min_by(|a, b| {
                            let ax = (points[*a].0 - cx).abs();
                            let bx = (points[*b].0 - cx).abs();
                            ax.total_cmp(&bx)
                        })
                    })
            }
            NavDirection::Up => {
                let order: Vec<usize> = (0..current_depth)
                    .rev()
                    .chain((current_depth..=max_depth).rev())
                    .collect();
                next_nonempty_depth(order, &rows)
                    .and_then(|depth| rows.get(&depth))
                    .and_then(|nodes| {
                        nodes.iter().copied().min_by(|a, b| {
                            let ax = (points[*a].0 - cx).abs();
                            let bx = (points[*b].0 - cx).abs();
                            ax.total_cmp(&bx)
                        })
                    })
            }
        };
    }

    if let Some(idx) = best_idx {
        app.selected_worktree = idx;
    }
}

fn move_worktree_level_siblings(app: &mut App, move_right: bool) {
    if app.worktrees.len() < 2 || app.selected_worktree >= app.worktrees.len() {
        return;
    }

    let root_branch = current_session_branch(app);
    let parents = worktree_parent_map(&app.worktrees, root_branch.as_str());
    let depths = graph_depths(&parents);
    let points = graph_layout(&parents);
    let current = app.selected_worktree;
    let current_depth = depths[current];
    let (cx, cy) = points[current];

    let mut best_idx: Option<usize> = None;
    let mut best_score = f32::MAX;
    for (idx, (x, y)) in points.iter().enumerate() {
        if idx == current || depths[idx] != current_depth {
            continue;
        }

        let dx = *x - cx;
        let in_direction = if move_right { dx > 0.02 } else { dx < -0.02 };
        if !in_direction {
            continue;
        }

        let score = dx.abs() + ((*y - cy).abs() * 1.4);
        if score < best_score {
            best_score = score;
            best_idx = Some(idx);
        }
    }

    if let Some(idx) = best_idx {
        app.selected_worktree = idx;
    }
}

fn move_worktree_level_vertical(app: &mut App, move_up: bool) {
    if app.worktrees.len() < 2 || app.selected_worktree >= app.worktrees.len() {
        return;
    }

    let root_branch = current_session_branch(app);
    let parents = worktree_parent_map(&app.worktrees, root_branch.as_str());
    let depths = graph_depths(&parents);
    let points = graph_layout(&parents);
    let current = app.selected_worktree;
    let current_depth = depths[current];
    let (cx, cy) = points[current];

    if move_up {
        if let Some(parent_idx) = parents.get(current).and_then(|parent| *parent) {
            app.selected_worktree = parent_idx;
            return;
        }

        if current_depth == 0 {
            return;
        }
    }

    let target_depth = if move_up {
        current_depth.saturating_sub(1)
    } else {
        current_depth + 1
    };

    let mut best_idx: Option<usize> = None;
    let mut best_score = f32::MAX;

    for (idx, depth) in depths.iter().enumerate() {
        if idx == current || *depth != target_depth {
            continue;
        }

        if !move_up && parents.get(idx).copied().flatten() != Some(current) {
            continue;
        }

        let (x, y) = points[idx];
        let score = (x - cx).abs() + (y - cy).abs();
        if score < best_score {
            best_score = score;
            best_idx = Some(idx);
        }
    }

    if best_idx.is_none() && !move_up {
        for (idx, depth) in depths.iter().enumerate() {
            if idx == current || *depth != target_depth {
                continue;
            }

            let (x, y) = points[idx];
            let score = (x - cx).abs() + (y - cy).abs();
            if score < best_score {
                best_score = score;
                best_idx = Some(idx);
            }
        }
    }

    if let Some(idx) = best_idx {
        app.selected_worktree = idx;
    }
}

fn create_root_for_app(app: &App) -> String {
    app.selected_worktree()
        .and_then(|wt| repo_container_from_path(wt.path.as_str()))
        .or_else(|| repo_container_from_path("."))
        .or_else(repo_root)
        .unwrap_or_else(|| ".".to_string())
}

fn branch_exists(root: &str, branch: &str) -> bool {
    Command::new("git")
        .args([
            "-C",
            root,
            "show-ref",
            "--verify",
            "--quiet",
            &format!("refs/heads/{}", branch),
        ])
        .status()
        .map(|status| status.success())
        .unwrap_or(false)
}

fn delete_branch_and_create_worktree(
    app: &App,
    root: &str,
    branch: &str,
) -> Result<String, Box<dyn Error>> {
    let delete = Command::new("git")
        .args(["-C", root, "branch", "-D", branch])
        .output()?;
    if !delete.status.success() {
        let stderr = sanitize_for_tui(String::from_utf8_lossy(&delete.stderr).as_ref())
            .trim()
            .to_string();
        let stdout = sanitize_for_tui(String::from_utf8_lossy(&delete.stdout).as_ref())
            .trim()
            .to_string();
        let reason = if !stderr.is_empty() { stderr } else { stdout };
        return Ok(format!("Failed deleting branch '{}': {}", branch, reason));
    }

    create_worktree(app, branch)
}

fn create_worktree(app: &App, branch: &str) -> Result<String, Box<dyn Error>> {
    let sanitized = branch.replace('/', "-");
    let root = create_root_for_app(app);
    let container = format!("{}/.gitfetch-worktrees", root);
    let _ = fs::create_dir_all(container.as_str());
    let path = format!("{}/.gitfetch-worktrees/{}", root, sanitized);
    if Path::new(path.as_str()).exists() {
        return Ok(format!(
            "Target path already exists: {} (pick another branch name)",
            path
        ));
    }
    let (start_point, parent_branch, source_path) = worktree_create_source(app);

    let output = Command::new("git")
        .args([
            "-C",
            root.as_str(),
            "worktree",
            "add",
            "-b",
            branch,
            path.as_str(),
            start_point.as_str(),
        ])
        .output()?;
    let stdout = sanitize_for_tui(String::from_utf8_lossy(&output.stdout).as_ref())
        .trim()
        .to_string();
    let stderr = sanitize_for_tui(String::from_utf8_lossy(&output.stderr).as_ref())
        .trim()
        .to_string();

    if output.status.success() {
        let verified = Command::new("git")
            .args(["-C", root.as_str(), "worktree", "list", "--porcelain"])
            .output()
            .ok()
            .map(|out| sanitize_for_tui(String::from_utf8_lossy(&out.stdout).as_ref()))
            .map(|list| {
                list.lines()
                    .any(|line| line.trim() == format!("worktree {}", path).as_str())
            })
            .unwrap_or(false);

        let mut message = if stdout.is_empty() {
            format!(
                "Created worktree '{}' at {} from {}",
                branch, path, start_point
            )
        } else {
            stdout
        };

        if app.new_worktree_base == WorktreeCreateBase::SelectedWithChanges {
            if let Some(diff) = capture_uncommitted_patch(source_path.as_str())? {
                if diff.trim().is_empty() {
                    message.push_str(" (no uncommitted tracked changes to apply)");
                } else {
                    let apply_result = run_git_with_input(
                        &["-C", path.as_str(), "apply", "--whitespace=nowarn", "-"],
                        diff.as_bytes(),
                    )?;
                    if apply_result.success {
                        message.push_str(" + carried uncommitted tracked changes");
                    } else {
                        message.push_str(" (created, but failed to apply uncommitted changes)");
                        if !apply_result.stderr.is_empty() {
                            message.push_str(": ");
                            message.push_str(apply_result.stderr.as_str());
                        }
                    }
                }
            }
        }

        let _ = save_parent_hint(root.as_str(), branch, parent_branch.as_str());

        if !verified {
            message.push_str(
                " (warning: creation reported success but worktree was not found in list)",
            );
        }

        Ok(message)
    } else if !stderr.is_empty() {
        let tail = stderr
            .lines()
            .rev()
            .find(|line| !line.trim().is_empty())
            .unwrap_or(stderr.as_str())
            .to_string();
        Ok(format!(
            "Failed creating worktree '{}' from '{}': {}",
            branch, start_point, tail
        ))
    } else if !stdout.is_empty() {
        Ok(stdout)
    } else {
        Ok("git worktree add failed".to_string())
    }
}

fn repo_root() -> Option<String> {
    let output = Command::new("git")
        .args(["rev-parse", "--show-toplevel"])
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }

    let root = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if root.is_empty() {
        None
    } else {
        Some(root)
    }
}

fn repo_container_from_path(path: &str) -> Option<String> {
    let output = Command::new("git")
        .args(["-C", path, "rev-parse", "--git-common-dir"])
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }

    let raw = String::from_utf8_lossy(&output.stdout).trim().to_string();
    if raw.is_empty() {
        None
    } else {
        let common_dir = if Path::new(raw.as_str()).is_absolute() {
            PathBuf::from(raw)
        } else {
            Path::new(path).join(raw)
        };
        let common_abs = fs::canonicalize(common_dir.as_path()).unwrap_or(common_dir);
        let parent = common_abs.parent()?.to_string_lossy().to_string();
        if parent.is_empty() {
            None
        } else {
            Some(parent)
        }
    }
}

fn parent_hint_map_path(root: &str) -> String {
    format!("{}/.gitfetch-worktrees/.parent-hints", root)
}

fn load_parent_hint_map(root: &str) -> BTreeMap<String, String> {
    let mut map = BTreeMap::new();
    let content = match fs::read_to_string(parent_hint_map_path(root)) {
        Ok(v) => v,
        Err(_) => return map,
    };

    for line in content.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }
        if let Some((child, parent)) = trimmed.split_once('\t') {
            let c = child.trim();
            let p = parent.trim();
            if !c.is_empty() && !p.is_empty() {
                map.insert(c.to_string(), p.to_string());
            }
        }
    }

    map
}

fn save_parent_hint(
    root: &str,
    child_branch: &str,
    parent_branch: &str,
) -> Result<(), Box<dyn Error>> {
    let mut map = load_parent_hint_map(root);
    map.insert(child_branch.to_string(), parent_branch.to_string());

    let mut lines = String::new();
    for (child, parent) in map {
        lines.push_str(child.as_str());
        lines.push('\t');
        lines.push_str(parent.as_str());
        lines.push('\n');
    }

    fs::write(parent_hint_map_path(root), lines)?;
    Ok(())
}

fn selected_branch_name(app: &App) -> String {
    if let Some(selected) = app.selected_worktree() {
        if !selected.detached && !selected.branch.is_empty() {
            return selected.branch.clone();
        }
        if !selected.head.is_empty() {
            return selected.head.clone();
        }
    }

    let raw = app.branch.trim();
    let name = raw
        .strip_prefix("HEAD (detached at ")
        .and_then(|value| value.strip_suffix(')'))
        .unwrap_or(raw);
    if name.is_empty() {
        "HEAD".to_string()
    } else {
        name.to_string()
    }
}

fn worktree_create_source(app: &App) -> (String, String, String) {
    match app.new_worktree_base {
        WorktreeCreateBase::Main => {
            let main = resolve_main_branch();
            (main.clone(), main, ".".to_string())
        }
        WorktreeCreateBase::Selected | WorktreeCreateBase::SelectedWithChanges => {
            let selected = selected_branch_name(app);
            let source_path = app
                .selected_worktree()
                .map(|wt| wt.path.clone())
                .unwrap_or_else(|| ".".to_string());
            (selected.clone(), selected, source_path)
        }
    }
}

fn resolve_main_branch() -> String {
    if let Some(main) = git_output(&["show-ref", "--verify", "--quiet", "refs/heads/main"]) {
        if main.is_empty() {
            return "main".to_string();
        }
    }
    if let Some(master) = git_output(&["show-ref", "--verify", "--quiet", "refs/heads/master"]) {
        if master.is_empty() {
            return "master".to_string();
        }
    }
    "main".to_string()
}

fn capture_uncommitted_patch(source_path: &str) -> Result<Option<String>, Box<dyn Error>> {
    let output = Command::new("git")
        .args(["-C", source_path, "diff", "--binary", "HEAD"])
        .output()?;
    if !output.status.success() {
        return Ok(None);
    }
    Ok(Some(sanitize_for_tui(
        String::from_utf8_lossy(&output.stdout).as_ref(),
    )))
}

struct CommandResult {
    success: bool,
    stderr: String,
}

fn run_git_with_input(args: &[&str], input: &[u8]) -> Result<CommandResult, Box<dyn Error>> {
    let mut child = Command::new("git")
        .args(args)
        .stdin(std::process::Stdio::piped())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .spawn()?;

    if let Some(stdin) = child.stdin.as_mut() {
        stdin.write_all(input)?;
    }

    let output = child.wait_with_output()?;
    Ok(CommandResult {
        success: output.status.success(),
        stderr: sanitize_for_tui(String::from_utf8_lossy(&output.stderr).as_ref())
            .trim()
            .to_string(),
    })
}

fn parse_branch_line(app: &mut App, line: &str) {
    let (branch, ahead, behind) = parse_branch_snapshot(line);
    app.branch = branch;
    app.ahead = ahead;
    app.behind = behind;
}

fn toggle_stage(app: &mut App) -> Result<(), Box<dyn Error>> {
    let item = match app.selected_item() {
        Some(entry) => entry,
        None => {
            app.status_line = "No item selected".to_string();
            return Ok(());
        }
    };

    if item.staged {
        app.status_line = run_git(&["restore", "--staged", "--", &item.path])?;
    } else {
        app.status_line = run_git(&["add", "--", &item.path])?;
    }

    Ok(())
}

fn refresh_selected_overview(app: &mut App) {
    let item = match app.selected_item() {
        Some(entry) => entry,
        None => {
            app.selected_overview = None;
            app.overview_scroll = 0;
            return;
        }
    };

    app.selected_overview = match item.kind {
        TreeKind::File => Some(build_file_overview(&FileEntry {
            path: item.path.clone(),
            staged: item.staged,
            unstaged: item.unstaged,
            untracked: item.untracked,
        })),
        TreeKind::Folder => Some(build_folder_overview(item, &app.files)),
    };

    let max_scroll = max_overview_scroll(app);
    if app.overview_scroll > max_scroll {
        app.overview_scroll = max_scroll;
    }
}

fn build_folder_overview(folder: &TreeItem, files: &[FileEntry]) -> FileOverview {
    let prefix = format!("{}/", folder.path);
    let mut total_added = 0usize;
    let mut total_removed = 0usize;
    let mut methods_added: HashSet<String> = HashSet::new();
    let mut methods_modified: HashSet<String> = HashSet::new();
    let mut methods_deleted: HashSet<String> = HashSet::new();
    let mut traditional_diff: Vec<DiffPreviewLine> = Vec::new();

    for file in files {
        if !(file.path == folder.path || file.path.starts_with(prefix.as_str())) {
            continue;
        }

        let overview = build_file_overview(file);
        total_added += overview.added_lines;
        total_removed += overview.removed_lines;
        methods_added.extend(overview.methods_added);
        methods_modified.extend(overview.methods_modified);
        methods_deleted.extend(overview.methods_deleted);

        if traditional_diff.len() < 24 {
            traditional_diff.push(DiffPreviewLine {
                kind: DiffPreviewKind::Meta,
                text: format!("file: {}", file.path),
            });
            for row in overview.traditional_diff.into_iter().take(6) {
                if traditional_diff.len() >= 24 {
                    break;
                }
                traditional_diff.push(row);
            }
        }
    }

    let methods_added = sorted_from_set(methods_added);
    let methods_modified = sorted_from_set(methods_modified);
    let methods_deleted = sorted_from_set(methods_deleted);
    let use_traditional_overview =
        methods_added.is_empty() && methods_modified.is_empty() && methods_deleted.is_empty();

    FileOverview {
        file: format!("{}/", folder.path),
        state: build_state_label(&FileEntry {
            path: folder.path.clone(),
            staged: folder.staged,
            unstaged: folder.unstaged,
            untracked: folder.untracked,
        }),
        added_lines: total_added,
        removed_lines: total_removed,
        methods_added,
        methods_modified,
        methods_deleted,
        traditional_diff,
        use_traditional_overview,
    }
}

fn build_file_overview(file: &FileEntry) -> FileOverview {
    let state = build_state_label(file);
    let mut added_lines = 0usize;
    let mut removed_lines = 0usize;
    let mut methods_added: Vec<String> = Vec::new();
    let mut methods_modified: Vec<String> = Vec::new();
    let mut methods_deleted: Vec<String> = Vec::new();
    let mut traditional_diff: Vec<DiffPreviewLine> = Vec::new();

    if file.untracked {
        let text = fs::read_to_string(&file.path).unwrap_or_default();
        added_lines = text.lines().count();
        methods_added = sorted_from_set(collect_methods_from_content(&text, &file.path));
        traditional_diff = preview_for_untracked(&text);
    } else if let Some(diff) = git_output(&[
        "diff",
        "--no-color",
        "--unified=0",
        "HEAD",
        "--",
        &file.path,
    ]) {
        let summary = summarize_diff(&diff, &file.path);
        added_lines = summary.added_lines;
        removed_lines = summary.removed_lines;
        methods_added = summary.methods_added;
        methods_modified = summary.methods_modified;
        methods_deleted = summary.methods_deleted;
        traditional_diff = summary.diff_preview;
    }

    let use_traditional_overview =
        methods_added.is_empty() && methods_modified.is_empty() && methods_deleted.is_empty();

    FileOverview {
        file: file.path.clone(),
        state,
        added_lines,
        removed_lines,
        methods_added,
        methods_modified,
        methods_deleted,
        traditional_diff,
        use_traditional_overview,
    }
}

fn build_state_label(file: &FileEntry) -> String {
    let mut states: Vec<&str> = Vec::new();
    if file.staged {
        states.push("staged");
    }
    if file.unstaged {
        states.push("unstaged");
    }
    if file.untracked {
        states.push("new");
    }
    if states.is_empty() {
        "clean".to_string()
    } else {
        states.join(", ")
    }
}

#[derive(Default)]
struct DiffSummary {
    added_lines: usize,
    removed_lines: usize,
    methods_added: Vec<String>,
    methods_modified: Vec<String>,
    methods_deleted: Vec<String>,
    diff_preview: Vec<DiffPreviewLine>,
}

fn summarize_diff(diff: &str, file_path: &str) -> DiffSummary {
    let mut added_methods: HashSet<String> = HashSet::new();
    let mut removed_methods: HashSet<String> = HashSet::new();
    let mut modified_hunks: HashSet<String> = HashSet::new();
    let mut diff_preview: Vec<DiffPreviewLine> = Vec::new();
    let mut current_hunk_method: Option<String> = None;
    let mut added_lines = 0usize;
    let mut removed_lines = 0usize;

    for line in diff.lines() {
        if line.starts_with("@@") {
            current_hunk_method = parse_hunk_header(line)
                .and_then(|header| extract_method_name(header.as_str(), file_path));
            push_preview_line(&mut diff_preview, DiffPreviewKind::Meta, line);
            continue;
        }

        if line.starts_with("+++") || line.starts_with("---") {
            push_preview_line(&mut diff_preview, DiffPreviewKind::Meta, line);
            continue;
        }

        if line.starts_with("diff --git") || line.starts_with("index ") {
            push_preview_line(&mut diff_preview, DiffPreviewKind::Meta, line);
            continue;
        }

        if let Some(rest) = line.strip_prefix('+') {
            added_lines += 1;
            if let Some(name) = current_hunk_method.as_ref() {
                modified_hunks.insert(name.clone());
            }
            if let Some(name) = extract_method_name(rest, file_path) {
                added_methods.insert(name);
            }
            push_preview_line(&mut diff_preview, DiffPreviewKind::Added, line);
            continue;
        }

        if let Some(rest) = line.strip_prefix('-') {
            removed_lines += 1;
            if let Some(name) = current_hunk_method.as_ref() {
                modified_hunks.insert(name.clone());
            }
            if let Some(name) = extract_method_name(rest, file_path) {
                removed_methods.insert(name);
            }
            push_preview_line(&mut diff_preview, DiffPreviewKind::Removed, line);
            continue;
        }

        push_preview_line(&mut diff_preview, DiffPreviewKind::Context, line);
    }

    let methods_added_set: HashSet<String> = added_methods
        .difference(&removed_methods)
        .cloned()
        .collect();
    let methods_deleted_set: HashSet<String> = removed_methods
        .difference(&added_methods)
        .cloned()
        .collect();
    let overlap_set: HashSet<String> = added_methods
        .intersection(&removed_methods)
        .cloned()
        .collect();
    let methods_modified_set: HashSet<String> = modified_hunks
        .union(&overlap_set)
        .cloned()
        .filter(|name| !methods_added_set.contains(name) && !methods_deleted_set.contains(name))
        .collect();

    DiffSummary {
        added_lines,
        removed_lines,
        methods_added: sorted_from_set(methods_added_set),
        methods_modified: sorted_from_set(methods_modified_set),
        methods_deleted: sorted_from_set(methods_deleted_set),
        diff_preview,
    }
}

fn push_preview_line(lines: &mut Vec<DiffPreviewLine>, kind: DiffPreviewKind, raw: &str) {
    if lines.len() >= 28 {
        return;
    }
    lines.push(DiffPreviewLine {
        kind,
        text: truncate_text(raw, 96),
    });
}

fn preview_for_untracked(content: &str) -> Vec<DiffPreviewLine> {
    let mut lines = Vec::new();
    for (idx, line) in content.lines().enumerate() {
        if idx >= 24 {
            break;
        }
        lines.push(DiffPreviewLine {
            kind: DiffPreviewKind::Added,
            text: format!("+{}", truncate_text(line, 95)),
        });
    }
    lines
}

fn sorted_from_set(set: HashSet<String>) -> Vec<String> {
    let mut v: Vec<String> = set.into_iter().collect();
    v.sort();
    v
}

fn parse_hunk_header(line: &str) -> Option<String> {
    let mut parts = line.split("@@");
    let _ = parts.next();
    let tail = parts.nth(1).unwrap_or_default().trim();
    if tail.is_empty() {
        None
    } else {
        Some(tail.to_string())
    }
}

fn collect_methods_from_content(content: &str, file_path: &str) -> HashSet<String> {
    let mut methods = HashSet::new();
    for line in content.lines() {
        if let Some(name) = extract_method_name(line, file_path) {
            methods.insert(name);
        }
    }
    methods
}

fn extract_method_name(line: &str, file_path: &str) -> Option<String> {
    let s = line.trim_start();
    let ext = file_extension(file_path);

    match ext {
        "py" => extract_python_method(s),
        "rs" => extract_rust_method(s),
        "js" | "jsx" | "ts" | "tsx" | "mjs" | "cjs" => extract_js_method(s),
        "go" => extract_go_method(s),
        _ => extract_general_method(s),
    }
}

fn file_extension(path: &str) -> &str {
    path.rsplit('.').next().unwrap_or_default()
}

fn extract_python_method(s: &str) -> Option<String> {
    if let Some(rest) = s.strip_prefix("def ") {
        return extract_identifier_until_paren(rest);
    }
    if let Some(rest) = s.strip_prefix("async def ") {
        return extract_identifier_until_paren(rest);
    }
    None
}

fn extract_rust_method(s: &str) -> Option<String> {
    if let Some(idx) = s.find(" fn ") {
        return extract_identifier_until_paren(&s[idx + 4..]);
    }
    if let Some(rest) = s.strip_prefix("fn ") {
        return extract_identifier_until_paren(rest);
    }
    None
}

fn extract_js_method(s: &str) -> Option<String> {
    if let Some(rest) = s.strip_prefix("function ") {
        return extract_identifier_until_paren(rest);
    }
    if let Some(rest) = s.strip_prefix("async function ") {
        return extract_identifier_until_paren(rest);
    }
    if let Some(rest) = s.strip_prefix("const ") {
        if rest.contains("=>") {
            let (left, _) = rest.split_once('=').unwrap_or(("", ""));
            let ident = left.trim();
            if is_identifier_like(ident) {
                return Some(ident.to_string());
            }
        }
    }
    None
}

fn extract_go_method(s: &str) -> Option<String> {
    if let Some(rest) = s.strip_prefix("func ") {
        if rest.starts_with('(') {
            let after_receiver = rest.split(')').nth(1).unwrap_or_default().trim_start();
            return extract_identifier_until_paren(after_receiver);
        }
        return extract_identifier_until_paren(rest);
    }
    None
}

fn extract_general_method(s: &str) -> Option<String> {
    if let Some(rest) = s.strip_prefix("function ") {
        return extract_identifier_until_paren(rest);
    }
    if let Some(rest) = s.strip_prefix("def ") {
        return extract_identifier_until_paren(rest);
    }
    None
}

fn extract_identifier_until_paren(text: &str) -> Option<String> {
    let name = text
        .split('(')
        .next()
        .unwrap_or_default()
        .trim()
        .trim_end_matches('{')
        .trim();

    if !is_identifier_like(name) {
        None
    } else {
        Some(name.to_string())
    }
}

fn is_identifier_like(value: &str) -> bool {
    if value.is_empty() {
        return false;
    }
    let mut chars = value.chars();
    let Some(first) = chars.next() else {
        return false;
    };
    if !(first == '_' || first.is_ascii_alphabetic()) {
        return false;
    }
    chars.all(|c| c == '_' || c.is_ascii_alphanumeric())
}

fn sanitize_for_tui(input: &str) -> String {
    let mut out = String::new();
    let mut chars = input.chars().peekable();

    while let Some(ch) = chars.next() {
        if ch == '\u{1b}' {
            match chars.peek().copied() {
                Some('[') => {
                    let _ = chars.next();
                    while let Some(c) = chars.next() {
                        if ('@'..='~').contains(&c) {
                            break;
                        }
                    }
                    continue;
                }
                Some(']') => {
                    let _ = chars.next();
                    while let Some(c) = chars.next() {
                        if c == '\u{7}' {
                            break;
                        }
                        if c == '\u{1b}' {
                            if let Some('\\') = chars.peek().copied() {
                                let _ = chars.next();
                                break;
                            }
                        }
                    }
                    continue;
                }
                _ => continue,
            }
        }

        if ch == '\n' || (ch >= ' ' && ch != '\u{7f}') {
            out.push(ch);
        } else if ch == '\t' {
            out.push_str("    ");
        }
    }

    out
}

fn run_git(args: &[&str]) -> Result<String, Box<dyn Error>> {
    let output = Command::new("git").args(args).output()?;
    let stdout = sanitize_for_tui(String::from_utf8_lossy(&output.stdout).as_ref())
        .trim()
        .to_string();
    let stderr = sanitize_for_tui(String::from_utf8_lossy(&output.stderr).as_ref())
        .trim()
        .to_string();

    if output.status.success() {
        if stdout.is_empty() {
            Ok(format!("✓ git {}", args.join(" ")))
        } else {
            Ok(stdout)
        }
    } else if !stderr.is_empty() {
        Ok(stderr)
    } else {
        Ok(format!("git {} failed", args.join(" ")))
    }
}

fn git_output(args: &[&str]) -> Option<String> {
    let output = Command::new("git").args(args).output().ok()?;
    if !output.status.success() {
        return None;
    }
    Some(sanitize_for_tui(
        String::from_utf8_lossy(&output.stdout).as_ref(),
    ))
}

fn push_with_upstream() -> Result<String, Box<dyn Error>> {
    let first = Command::new("git").args(["push"]).output()?;
    let first_stdout = sanitize_for_tui(String::from_utf8_lossy(&first.stdout).as_ref())
        .trim()
        .to_string();
    let first_stderr = sanitize_for_tui(String::from_utf8_lossy(&first.stderr).as_ref())
        .trim()
        .to_string();

    if first.status.success() {
        if first_stdout.is_empty() {
            return Ok("✓ git push".to_string());
        }
        return Ok(first_stdout);
    }

    let error_text = if !first_stderr.is_empty() {
        first_stderr.clone()
    } else {
        first_stdout.clone()
    };

    let needs_upstream = error_text.contains("has no upstream branch")
        || error_text.contains("--set-upstream")
        || error_text.contains("set upstream");

    if !needs_upstream {
        if error_text.is_empty() {
            return Ok("git push failed".to_string());
        }
        return Ok(error_text);
    }

    let remote = preferred_remote()?;
    let second = Command::new("git")
        .args(["push", "-u", remote.as_str(), "HEAD"])
        .output()?;
    let second_stdout = sanitize_for_tui(String::from_utf8_lossy(&second.stdout).as_ref())
        .trim()
        .to_string();
    let second_stderr = sanitize_for_tui(String::from_utf8_lossy(&second.stderr).as_ref())
        .trim()
        .to_string();

    if second.status.success() {
        if second_stdout.is_empty() {
            Ok(format!("✓ git push -u {} HEAD", remote))
        } else {
            Ok(format!(
                "Set upstream to {} and pushed\n{}",
                remote, second_stdout
            ))
        }
    } else if !second_stderr.is_empty() {
        Ok(second_stderr)
    } else if !second_stdout.is_empty() {
        Ok(second_stdout)
    } else {
        Ok(format!("git push -u {} HEAD failed", remote))
    }
}

fn commit_and_push_worktree(path: &str, message: &str) -> Result<String, Box<dyn Error>> {
    let add = Command::new("git")
        .args(["-C", path, "add", "."])
        .output()?;
    if !add.status.success() {
        let stderr = sanitize_for_tui(String::from_utf8_lossy(&add.stderr).as_ref())
            .trim()
            .to_string();
        let stdout = sanitize_for_tui(String::from_utf8_lossy(&add.stdout).as_ref())
            .trim()
            .to_string();
        let reason = if !stderr.is_empty() { stderr } else { stdout };
        return Ok(format!(
            "git add failed in {}: {}",
            path,
            single_line(reason.as_str())
        ));
    }

    let commit = Command::new("git")
        .args(["-C", path, "commit", "-m", message])
        .output()?;
    let commit_stdout = sanitize_for_tui(String::from_utf8_lossy(&commit.stdout).as_ref())
        .trim()
        .to_string();
    let commit_stderr = sanitize_for_tui(String::from_utf8_lossy(&commit.stderr).as_ref())
        .trim()
        .to_string();

    let nothing_to_commit = !commit.status.success()
        && (commit_stdout.contains("nothing to commit")
            || commit_stderr.contains("nothing to commit")
            || commit_stderr.contains("no changes added to commit"));

    if !commit.status.success() && !nothing_to_commit {
        let reason = if !commit_stderr.is_empty() {
            commit_stderr
        } else {
            commit_stdout
        };
        return Ok(format!(
            "git commit failed in {}: {}",
            path,
            single_line(reason.as_str())
        ));
    }

    let push = push_with_upstream_at(path)?;
    if nothing_to_commit {
        Ok(format!(
            "No new commit in {}; pushed current HEAD - {}",
            path,
            single_line(push.as_str())
        ))
    } else {
        let commit_line = if !commit_stdout.is_empty() {
            single_line(commit_stdout.as_str())
        } else if !commit_stderr.is_empty() {
            single_line(commit_stderr.as_str())
        } else {
            "commit ok".to_string()
        };
        Ok(format!(
            "Committed+Pushed in {} - {} | {}",
            path,
            commit_line,
            single_line(push.as_str())
        ))
    }
}

fn push_with_upstream_at(path: &str) -> Result<String, Box<dyn Error>> {
    let remote = preferred_remote_at(path)?;
    let push = Command::new("git")
        .args(["-C", path, "push", "-u", remote.as_str(), "HEAD"])
        .output()?;
    let push_stdout = sanitize_for_tui(String::from_utf8_lossy(&push.stdout).as_ref())
        .trim()
        .to_string();
    let push_stderr = sanitize_for_tui(String::from_utf8_lossy(&push.stderr).as_ref())
        .trim()
        .to_string();

    if push.status.success() {
        Ok(if push_stdout.is_empty() {
            format!("✓ git push -u {} HEAD", remote)
        } else {
            format!("Set upstream to {} and pushed\n{}", remote, push_stdout)
        })
    } else if !push_stderr.is_empty() {
        Ok(push_stderr)
    } else if !push_stdout.is_empty() {
        Ok(push_stdout)
    } else {
        Ok(format!("git push -u {} HEAD failed", remote))
    }
}

fn preferred_remote_at(path: &str) -> Result<String, Box<dyn Error>> {
    let output = Command::new("git").args(["-C", path, "remote"]).output()?;
    let stdout = String::from_utf8_lossy(&output.stdout);
    let remotes: Vec<&str> = stdout
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty())
        .collect();

    if remotes.iter().any(|name| *name == "origin") {
        Ok("origin".to_string())
    } else if let Some(first) = remotes.first() {
        Ok((*first).to_string())
    } else {
        Ok("origin".to_string())
    }
}

fn preferred_remote() -> Result<String, Box<dyn Error>> {
    let output = Command::new("git").args(["remote"]).output()?;
    let stdout = String::from_utf8_lossy(&output.stdout);
    let remotes: Vec<&str> = stdout
        .lines()
        .map(str::trim)
        .filter(|line| !line.is_empty())
        .collect();

    if remotes.iter().any(|name| *name == "origin") {
        Ok("origin".to_string())
    } else if let Some(first) = remotes.first() {
        Ok((*first).to_string())
    } else {
        Ok("origin".to_string())
    }
}

fn draw_ui(frame: &mut ratatui::Frame<'_>, app: &App) {
    frame.render_widget(Clear, frame.area());
    frame.render_widget(
        Block::default().style(Style::default().bg(Color::Black).fg(Color::White)),
        frame.area(),
    );

    if matches!(app.mode, Mode::AgentPopup) {
        draw_agent_popup(frame, app);
        return;
    }

    if app.view_mode == ViewMode::Changes {
        let columns = Layout::default()
            .direction(Direction::Horizontal)
            .spacing(1)
            .constraints([
                Constraint::Percentage(22),
                Constraint::Percentage(56),
                Constraint::Percentage(22),
            ])
            .split(frame.area());

        let right = Layout::default()
            .direction(Direction::Vertical)
            .spacing(1)
            .constraints([Constraint::Percentage(58), Constraint::Percentage(42)])
            .split(columns[2]);

        draw_files_panel(frame, app, columns[0]);
        draw_selected_overview_panel(frame, app, columns[1]);
        draw_pulse_panel(frame, app, right[0]);
        draw_changes_actions_panel(frame, right[1]);
    } else {
        let columns = Layout::default()
            .direction(Direction::Horizontal)
            .spacing(1)
            .constraints([Constraint::Percentage(72), Constraint::Percentage(28)])
            .split(frame.area());

        let right = Layout::default()
            .direction(Direction::Vertical)
            .spacing(1)
            .constraints([Constraint::Percentage(60), Constraint::Percentage(40)])
            .split(columns[1]);

        draw_worktree_canvas_panel(frame, app, columns[0]);
        draw_worktree_details_panel(frame, app, right[0]);
        draw_worktree_actions_panel(frame, app, right[1]);
    }

    if matches!(app.mode, Mode::CommitInput) {
        draw_commit_modal(frame, app);
    }

    if matches!(app.mode, Mode::WorktreeCommitPushInput) {
        draw_worktree_commit_push_modal(frame, app);
    }

    if matches!(app.mode, Mode::WorktreeCreateInput) {
        draw_worktree_create_modal(frame, app);
    }

    if matches!(app.mode, Mode::WorktreeBranchConflictConfirm) {
        draw_branch_conflict_confirm_modal(frame, app);
    }

    if matches!(app.mode, Mode::QuitWithSessionsConfirm) {
        draw_quit_with_sessions_modal(frame, app);
    }

    if app.view_mode == ViewMode::Worktrees && app.show_panel_help {
        draw_worktree_help_modal(frame, app);
    }
}

fn draw_files_panel(frame: &mut ratatui::Frame<'_>, app: &App, area: Rect) {
    frame.render_widget(Clear, area);

    let content_width = area.width.saturating_sub(6) as usize;
    let mut items: Vec<ListItem<'_>> = Vec::new();
    let mut index_map: Vec<Option<usize>> = Vec::new();
    let count_width = app
        .tree_items
        .iter()
        .map(|item| {
            item.added_lines
                .max(item.removed_lines)
                .to_string()
                .chars()
                .count()
        })
        .max()
        .unwrap_or(1)
        .max(4);

    let unstaged_indices: Vec<usize> = app
        .tree_items
        .iter()
        .enumerate()
        .filter(|(_, item)| item.unstaged || item.untracked)
        .map(|(idx, _)| idx)
        .collect();
    let staged_indices: Vec<usize> = app
        .tree_items
        .iter()
        .enumerate()
        .filter(|(_, item)| item.staged)
        .map(|(idx, _)| idx)
        .collect();

    push_section_header(
        &mut items,
        &mut index_map,
        "unstaged",
        unstaged_indices.len(),
    );
    if unstaged_indices.is_empty() {
        items.push(ListItem::new(Line::from(Span::styled(
            "  clean",
            Style::default().fg(Color::DarkGray),
        ))));
        index_map.push(None);
    } else {
        for idx in unstaged_indices {
            push_tree_row(
                &mut items,
                &mut index_map,
                idx,
                &app.tree_items[idx],
                content_width,
                count_width,
            );
        }
    }

    items.push(ListItem::new(Line::from("")));
    index_map.push(None);

    push_section_header(&mut items, &mut index_map, "staged", staged_indices.len());
    if staged_indices.is_empty() {
        items.push(ListItem::new(Line::from(Span::styled(
            "  clean",
            Style::default().fg(Color::DarkGray),
        ))));
        index_map.push(None);
    } else {
        for idx in staged_indices {
            push_tree_row(
                &mut items,
                &mut index_map,
                idx,
                &app.tree_items[idx],
                content_width,
                count_width,
            );
        }
    }

    let selected_render_idx = index_map
        .iter()
        .position(|mapped| *mapped == Some(app.selected));

    let mut state = ListState::default();
    if let Some(idx) = selected_render_idx {
        state.select(Some(idx));
    }

    let border_color = if app.active_pane == ActivePane::Files {
        Color::Cyan
    } else {
        Color::Gray
    };

    let list = List::new(items)
        .block(
            Block::default()
                .title("changed files")
                .borders(Borders::ALL)
                .style(Style::default().bg(Color::Black))
                .border_style(Style::default().fg(border_color)),
        )
        .highlight_style(
            Style::default()
                .fg(Color::White)
                .bg(Color::Rgb(42, 58, 86))
                .add_modifier(Modifier::BOLD),
        )
        .highlight_symbol("▶ ")
        .style(Style::default().bg(Color::Black));

    frame.render_stateful_widget(list, area, &mut state);
}

fn push_section_header(
    items: &mut Vec<ListItem<'_>>,
    index_map: &mut Vec<Option<usize>>,
    title: &str,
    count: usize,
) {
    items.push(ListItem::new(Line::from(vec![Span::styled(
        format!("{} ({})", title, count),
        Style::default()
            .fg(Color::Gray)
            .add_modifier(Modifier::BOLD),
    )])));
    index_map.push(None);
}

fn push_tree_row(
    items: &mut Vec<ListItem<'_>>,
    index_map: &mut Vec<Option<usize>>,
    idx: usize,
    item: &TreeItem,
    content_width: usize,
    count_width: usize,
) {
    let mut spans: Vec<Span<'_>> = Vec::new();
    let name_color = if item.kind == TreeKind::Folder {
        Color::LightYellow
    } else {
        Color::LightCyan
    };

    let plus_text = format!("+{:>width$}", item.added_lines, width = count_width);
    let minus_text = format!("-{:>width$}", item.removed_lines, width = count_width);
    let right_len = plus_text.chars().count() + 1 + minus_text.chars().count();
    let label_col = content_width.saturating_sub(right_len).max(8);
    let label = truncate_text(item.label.as_str(), label_col);
    let padding = label_col.saturating_sub(label.chars().count());

    spans.push(Span::styled(label, Style::default().fg(name_color)));
    spans.push(Span::raw(" ".repeat(padding)));
    spans.push(Span::styled(plus_text, Style::default().fg(Color::Green)));
    spans.push(Span::raw(" "));
    spans.push(Span::styled(minus_text, Style::default().fg(Color::Red)));

    items.push(ListItem::new(Line::from(spans)));
    index_map.push(Some(idx));
}

fn draw_selected_overview_panel(frame: &mut ratatui::Frame<'_>, app: &App, area: Rect) {
    frame.render_widget(Clear, area);

    let info = app.selected_overview.as_ref();

    let mut lines: Vec<Line<'_>> = Vec::new();
    if let Some(info) = info {
        lines.push(Line::from(vec![
            Span::styled("file: ", Style::default().fg(Color::Gray)),
            Span::styled(info.file.as_str(), Style::default().fg(Color::White)),
        ]));
        lines.push(Line::from(vec![
            Span::styled("state: ", Style::default().fg(Color::Gray)),
            Span::styled(info.state.as_str(), Style::default().fg(Color::Cyan)),
        ]));
        lines.push(Line::from(""));
        lines.push(Line::from(vec![Span::styled(
            "files changes",
            Style::default()
                .fg(Color::White)
                .add_modifier(Modifier::BOLD),
        )]));
        lines.push(Line::from(vec![
            Span::styled(
                "+",
                Style::default()
                    .fg(Color::Green)
                    .add_modifier(Modifier::BOLD),
            ),
            Span::styled(
                info.added_lines.to_string(),
                Style::default().fg(Color::Green),
            ),
            Span::raw("  "),
            Span::styled(
                "-",
                Style::default().fg(Color::Red).add_modifier(Modifier::BOLD),
            ),
            Span::styled(
                info.removed_lines.to_string(),
                Style::default().fg(Color::Red),
            ),
        ]));
        lines.push(Line::from(""));

        if info.use_traditional_overview {
            if info.traditional_diff.is_empty() {
                lines.push(Line::from("No diff preview available"));
            } else {
                lines.push(Line::from("diff preview:"));
                for row in info.traditional_diff.iter().take(24) {
                    let color = match row.kind {
                        DiffPreviewKind::Added => Color::Green,
                        DiffPreviewKind::Removed => Color::Red,
                        DiffPreviewKind::Meta => Color::Blue,
                        DiffPreviewKind::Context => Color::Gray,
                    };
                    lines.push(Line::from(Span::styled(
                        row.text.as_str(),
                        Style::default().fg(color),
                    )));
                }
            }
        } else {
            push_method_section(
                &mut lines,
                "methods added",
                Color::LightGreen,
                &info.methods_added,
            );
            push_method_section(
                &mut lines,
                "methods modified",
                Color::Yellow,
                &info.methods_modified,
            );
            push_method_section(
                &mut lines,
                "methods deleted",
                Color::LightRed,
                &info.methods_deleted,
            );
        }
    } else {
        lines.push(Line::from("No changed file selected"));
    }

    let panel = Paragraph::new(lines)
        .scroll((app.overview_scroll, 0))
        .block(
            Block::default()
                .title("selected file overview")
                .borders(Borders::ALL)
                .style(Style::default().bg(Color::Black))
                .border_style(
                    Style::default().fg(if app.active_pane == ActivePane::Overview {
                        Color::Cyan
                    } else {
                        Color::Gray
                    }),
                ),
        )
        .style(Style::default().bg(Color::Black).fg(Color::White))
        .alignment(Alignment::Left);

    frame.render_widget(panel, area);
}

fn push_method_section(lines: &mut Vec<Line<'_>>, title: &str, color: Color, names: &[String]) {
    lines.push(Line::from(vec![Span::styled(
        title.to_string(),
        Style::default().fg(color),
    )]));
    if names.is_empty() {
        lines.push(Line::from("- none"));
    } else {
        for name in names.iter().take(8) {
            lines.push(Line::from(vec![
                Span::raw("- "),
                Span::styled(truncate_text(name, 56), Style::default().fg(Color::White)),
            ]));
        }
    }
    lines.push(Line::from(""));
}

fn draw_pulse_panel(frame: &mut ratatui::Frame<'_>, app: &App, area: Rect) {
    let staged_count = app.files.iter().filter(|f| f.staged).count();
    let unstaged_count = app
        .files
        .iter()
        .filter(|f| f.unstaged || f.untracked)
        .count();

    let status_limit = area.width.saturating_sub(12) as usize;
    let status_text = truncate_text(
        single_line(app.status_line.as_str()).as_str(),
        status_limit.max(10),
    );

    let info = vec![
        Line::from(vec![
            Span::styled("Branch: ", Style::default().fg(Color::Gray)),
            Span::styled(
                app.branch.as_str(),
                Style::default()
                    .fg(Color::Cyan)
                    .add_modifier(Modifier::BOLD),
            ),
        ]),
        Line::from(vec![
            Span::styled("Ahead: ", Style::default().fg(Color::Gray)),
            Span::styled(app.ahead.to_string(), Style::default().fg(Color::Green)),
            Span::raw("  "),
            Span::styled("Behind: ", Style::default().fg(Color::Gray)),
            Span::styled(app.behind.to_string(), Style::default().fg(Color::Yellow)),
        ]),
        Line::from(""),
        Line::from(vec![
            Span::styled("Staged files: ", Style::default().fg(Color::Gray)),
            Span::styled(staged_count.to_string(), Style::default().fg(Color::Green)),
        ]),
        Line::from(vec![
            Span::styled("Unstaged files: ", Style::default().fg(Color::Gray)),
            Span::styled(
                unstaged_count.to_string(),
                Style::default().fg(Color::Yellow),
            ),
        ]),
        Line::from(""),
        Line::from(Span::styled(
            "Live refresh every ~700ms",
            Style::default().fg(Color::Blue),
        )),
        Line::from(""),
        Line::from(vec![
            Span::styled("Status: ", Style::default().fg(Color::Gray)),
            Span::styled(status_text, Style::default().fg(Color::White)),
        ]),
    ];

    let panel = Paragraph::new(info)
        .block(
            Block::default()
                .title("pulse")
                .borders(Borders::ALL)
                .style(Style::default().bg(Color::Black))
                .border_style(Style::default().fg(Color::Gray)),
        )
        .style(Style::default().bg(Color::Black).fg(Color::White))
        .alignment(Alignment::Left);

    frame.render_widget(panel, area);
}

fn draw_changes_actions_panel(frame: &mut ratatui::Frame<'_>, area: Rect) {
    let lines = vec![
        Line::from(vec![
            Span::styled("w", Style::default().fg(Color::LightBlue)),
            Span::raw(" worktree canvas"),
        ]),
        Line::from(vec![
            Span::styled("h/l", Style::default().fg(Color::LightBlue)),
            Span::raw(" focus files/overview"),
        ]),
        Line::from(vec![
            Span::styled("j/k", Style::default().fg(Color::LightBlue)),
            Span::raw(" move selection/scroll"),
        ]),
        Line::from(vec![
            Span::styled("space|enter", Style::default().fg(Color::LightGreen)),
            Span::raw(" stage or unstage"),
        ]),
        Line::from(vec![
            Span::styled("c", Style::default().fg(Color::Yellow)),
            Span::raw(" commit"),
        ]),
        Line::from(vec![
            Span::styled("p", Style::default().fg(Color::Magenta)),
            Span::raw(" push"),
        ]),
        Line::from(vec![
            Span::styled("s", Style::default().fg(Color::LightYellow)),
            Span::raw(" stash changes"),
        ]),
        Line::from(vec![
            Span::styled("S", Style::default().fg(Color::Yellow)),
            Span::raw(" stash pop"),
        ]),
        Line::from(vec![
            Span::styled("r", Style::default().fg(Color::Cyan)),
            Span::raw(" refresh"),
        ]),
        Line::from(vec![
            Span::styled("q", Style::default().fg(Color::Red)),
            Span::raw(" quit"),
        ]),
    ];

    let panel = Paragraph::new(lines)
        .block(
            Block::default()
                .title("actions")
                .borders(Borders::ALL)
                .style(Style::default().bg(Color::Black))
                .border_style(Style::default().fg(Color::Gray)),
        )
        .style(Style::default().bg(Color::Black).fg(Color::White))
        .alignment(Alignment::Left);

    frame.render_widget(panel, area);
}

fn draw_worktree_canvas_panel(frame: &mut ratatui::Frame<'_>, app: &App, area: Rect) {
    let border_color = if app.worktree_focus == WorktreePane::Canvas {
        Color::Cyan
    } else {
        Color::Gray
    };
    let block = Block::default()
        .title("worktree canvas [?]")
        .borders(Borders::ALL)
        .border_style(Style::default().fg(border_color))
        .style(Style::default().bg(Color::Black));

    let inner = block.inner(area);
    frame.render_widget(block, area);
    frame.render_widget(Clear, inner);
    frame.render_widget(
        Paragraph::new("").style(Style::default().bg(Color::Black)),
        inner,
    );

    let root_branch = current_session_branch(app);
    let main_label = canvas_root_label(app, root_branch.as_str());
    let main_anchor_x = inner.x.saturating_add(inner.width / 2);
    let main_anchor_y = inner.y.saturating_add(1);
    let main_x = main_anchor_x.saturating_sub((main_label.chars().count() as u16) / 2);
    frame.render_widget(
        Paragraph::new(main_label.as_str()).style(
            Style::default()
                .fg(Color::Black)
                .bg(Color::LightMagenta)
                .add_modifier(Modifier::BOLD),
        ),
        Rect::new(main_x, main_anchor_y, main_label.chars().count() as u16, 1),
    );

    if app.worktrees.is_empty() {
        frame.render_widget(
            Paragraph::new("No worktrees. Press 'a' to create one.")
                .alignment(Alignment::Center)
                .style(Style::default().fg(Color::DarkGray)),
            inner,
        );
        return;
    }

    let parents = worktree_parent_map(&app.worktrees, root_branch.as_str());
    let positions = render_positions(inner, &parents);
    for (idx, parent) in parents.iter().enumerate() {
        let to = positions[idx];
        let from = if let Some(parent_idx) = parent {
            positions[*parent_idx]
        } else {
            (main_anchor_x, main_anchor_y)
        };
        draw_canvas_edge(frame, inner, from, to);
    }

    for (idx, entry) in app.worktrees.iter().enumerate() {
        let selected = idx == app.selected_worktree;
        let label = canvas_node_label(app, entry, selected);
        let (anchor_x, anchor_y) = positions[idx];
        let label_width = label.chars().count() as u16;
        let mut x = anchor_x.saturating_sub(label_width / 2);
        if x + label_width >= inner.right() {
            x = inner.right().saturating_sub(label_width + 1);
        }
        if x <= inner.x {
            x = inner.x.saturating_add(1);
        }
        let node_rect = Rect::new(
            x,
            anchor_y.min(inner.bottom().saturating_sub(1)),
            label_width,
            1,
        );
        let style = if selected {
            Style::default()
                .fg(Color::Black)
                .bg(Color::LightCyan)
                .add_modifier(Modifier::BOLD)
        } else if entry.dirty {
            Style::default().fg(Color::Yellow)
        } else {
            Style::default().fg(Color::White)
        };
        frame.render_widget(Paragraph::new(label).style(style), node_rect);
    }
}

fn canvas_root_label(_app: &App, root_branch: &str) -> String {
    format!("HEAD ({})", truncate_text(root_branch, 18))
}

fn canvas_node_label(app: &App, entry: &WorktreeEntry, selected: bool) -> String {
    let mut name = if entry.detached {
        "detached".to_string()
    } else {
        entry.branch.clone()
    };
    if name.len() > 20 {
        name = truncate_text(name.as_str(), 20);
    }

    let state = if entry.dirty { "dirty" } else { "clean" };
    let agent = agent_badge_for_node(app, entry.path.as_str());
    if selected {
        format!("[{name} | {state}{agent}]")
    } else {
        format!("({name} | {state}{agent})")
    }
}

fn agent_badge_for_node(app: &App, path: &str) -> String {
    let Some(session) = app.agent_sessions.get(path) else {
        return String::new();
    };

    let in_foreground = matches!(app.mode, Mode::AgentPopup)
        && app
            .agent_popup_path
            .as_deref()
            .map(|p| p == path)
            .unwrap_or(false);

    let marker = match session.state {
        AgentState::Launching | AgentState::Running => {
            if in_foreground {
                " ...fg"
            } else {
                " ...bg"
            }
        }
        AgentState::Done => " ✓",
        AgentState::Failed => " !",
    };
    marker.to_string()
}

fn render_positions(area: Rect, parents: &[Option<usize>]) -> Vec<(u16, u16)> {
    let logical = graph_layout(parents);
    let mut points = Vec::with_capacity(logical.len());
    let width = area.width.saturating_sub(8).max(8) as f32;
    let height = area.height.saturating_sub(7).max(6) as f32;

    for (x, y) in logical {
        let sx = (x * width).round().max(0.0) as u16;
        let sy = (y * height).round().max(0.0) as u16;
        points.push((area.x + 4 + sx, area.y + 4 + sy));
    }

    points
}

fn graph_layout(parents: &[Option<usize>]) -> Vec<(f32, f32)> {
    let count = parents.len();
    if count == 0 {
        return Vec::new();
    }

    let depths = graph_depths(parents);
    let max_depth = depths.iter().copied().max().unwrap_or(0).max(1);
    let mut by_depth: BTreeMap<usize, Vec<usize>> = BTreeMap::new();
    for (idx, depth) in depths.iter().enumerate() {
        by_depth.entry(*depth).or_default().push(idx);
    }

    let mut positions = vec![(0.5f32, 0.5f32); count];
    for (depth, nodes) in by_depth {
        let n = nodes.len().max(1);
        for (rank, idx) in nodes.iter().enumerate() {
            let x = (rank as f32 + 1.0) / (n as f32 + 1.0);
            let y = 0.15 + ((depth as f32 + 1.0) / (max_depth as f32 + 1.0)) * 0.78;
            positions[*idx] = (x, y);
        }
    }

    for _ in 0..24 {
        let mut forces = vec![(0.0f32, 0.0f32); count];

        for i in 0..count {
            for j in (i + 1)..count {
                let dx = positions[i].0 - positions[j].0;
                let dy = positions[i].1 - positions[j].1;
                let dist_sq = (dx * dx + dy * dy).max(0.0006);
                let force = 0.0022 / dist_sq;
                let nx = dx / dist_sq.sqrt();
                let ny = dy / dist_sq.sqrt();
                forces[i].0 += nx * force;
                forces[i].1 += ny * force;
                forces[j].0 -= nx * force;
                forces[j].1 -= ny * force;
            }
        }

        for (idx, parent_opt) in parents.iter().enumerate() {
            let (tx, ty) = if let Some(parent_idx) = parent_opt {
                positions[*parent_idx]
            } else {
                (0.5, 0.06)
            };

            let dx = tx - positions[idx].0;
            let dy = ty - positions[idx].1;
            let dist = (dx * dx + dy * dy).sqrt().max(0.001);
            let desired = if parent_opt.is_some() { 0.18 } else { 0.24 };
            let spring = (dist - desired) * 0.024;
            forces[idx].0 += (dx / dist) * spring;
            forces[idx].1 += (dy / dist) * spring;

            let target_y = 0.15 + ((depths[idx] as f32 + 1.0) / (max_depth as f32 + 1.0)) * 0.78;
            forces[idx].1 += (target_y - positions[idx].1) * 0.015;
            forces[idx].0 += (0.5 - positions[idx].0) * 0.002;
        }

        for idx in 0..count {
            positions[idx].0 = (positions[idx].0 + forces[idx].0).clamp(0.06, 0.94);
            positions[idx].1 = (positions[idx].1 + forces[idx].1).clamp(0.12, 0.95);
        }
    }

    positions
}

fn graph_depths(parents: &[Option<usize>]) -> Vec<usize> {
    fn depth_for(i: usize, parents: &[Option<usize>], cache: &mut [Option<usize>]) -> usize {
        if let Some(depth) = cache[i] {
            return depth;
        }

        let depth = match parents[i] {
            Some(parent) if parent != i => depth_for(parent, parents, cache) + 1,
            _ => 0,
        };
        cache[i] = Some(depth);
        depth
    }

    let mut cache = vec![None; parents.len()];
    (0..parents.len())
        .map(|i| depth_for(i, parents, &mut cache))
        .collect()
}

fn worktree_parent_map(worktrees: &[WorktreeEntry], root_branch: &str) -> Vec<Option<usize>> {
    let mut branch_to_idx: BTreeMap<String, usize> = BTreeMap::new();
    for (idx, wt) in worktrees.iter().enumerate() {
        if !wt.detached && !wt.branch.is_empty() {
            branch_to_idx.entry(wt.branch.clone()).or_insert(idx);
        }
    }

    let mut parents = vec![None; worktrees.len()];
    for (idx, wt) in worktrees.iter().enumerate() {
        if wt.detached || is_root_branch(wt.branch.as_str(), root_branch) {
            continue;
        }

        if let Some(hint) = wt.parent_hint.as_deref() {
            if let Some(parent_idx) = branch_to_idx.get(hint) {
                if *parent_idx != idx {
                    parents[idx] = Some(*parent_idx);
                    continue;
                }
            }
        }

        if let Some(parent_idx) = find_branch_parent_idx(idx, wt.branch.as_str(), &branch_to_idx) {
            parents[idx] = Some(parent_idx);
        }
    }

    let root_idx = worktrees
        .iter()
        .enumerate()
        .find_map(|(idx, wt)| {
            if !wt.detached && wt.branch == root_branch && wt.is_current {
                Some(idx)
            } else {
                None
            }
        })
        .or_else(|| {
            worktrees.iter().enumerate().find_map(|(idx, wt)| {
                if !wt.detached && wt.branch == root_branch {
                    Some(idx)
                } else {
                    None
                }
            })
        });

    if let Some(root_idx) = root_idx {
        for (idx, wt) in worktrees.iter().enumerate() {
            if idx == root_idx {
                continue;
            }
            if wt.detached {
                continue;
            }
            if parents[idx].is_none() {
                parents[idx] = Some(root_idx);
            }
        }
    }

    parents
}

fn find_branch_parent_idx(
    current_idx: usize,
    branch: &str,
    branch_to_idx: &BTreeMap<String, usize>,
) -> Option<usize> {
    let mut parts: Vec<&str> = branch.split('/').collect();
    while parts.len() > 1 {
        parts.pop();
        let candidate = parts.join("/");
        if let Some(idx) = branch_to_idx.get(candidate.as_str()) {
            if *idx != current_idx {
                return Some(*idx);
            }
        }
    }
    None
}

fn is_root_branch(branch: &str, root_branch: &str) -> bool {
    branch == root_branch
}

fn worktree_parent_label(app: &App, parents: &[Option<usize>]) -> String {
    if app.selected_worktree >= app.worktrees.len() {
        return current_session_branch(app);
    }

    if let Some(parent_idx) = parents.get(app.selected_worktree).and_then(|v| *v) {
        if let Some(parent) = app.worktrees.get(parent_idx) {
            if parent.detached {
                return "detached".to_string();
            }
            return parent.branch.clone();
        }
    }

    current_session_branch(app)
}

fn current_session_branch(app: &App) -> String {
    let raw = app.branch.trim();
    let name = raw
        .strip_prefix("HEAD (detached at ")
        .and_then(|value| value.strip_suffix(')'))
        .unwrap_or(raw);
    if name.is_empty() {
        "current".to_string()
    } else {
        name.to_string()
    }
}

fn draw_canvas_edge(frame: &mut ratatui::Frame<'_>, area: Rect, from: (u16, u16), to: (u16, u16)) {
    let mut x0 = from.0 as i32;
    let mut y0 = from.1 as i32 + 1;
    let x1 = to.0 as i32;
    let y1 = to.1 as i32;
    let edge_char = edge_base_char(x1 - x0, y1 - y0);

    let dx = (x1 - x0).abs();
    let sx = if x0 < x1 { 1 } else { -1 };
    let dy = -(y1 - y0).abs();
    let sy = if y0 < y1 { 1 } else { -1 };
    let mut err = dx + dy;
    let mut step = 0usize;

    loop {
        if x0 >= area.x as i32
            && x0 < area.right() as i32
            && y0 >= area.y as i32
            && y0 < area.bottom() as i32
        {
            let glyph = if step % 9 == 0 {
                "o"
            } else if step % 4 == 0 {
                ":"
            } else {
                edge_char
            };
            frame.render_widget(
                Paragraph::new(glyph).style(Style::default().fg(Color::DarkGray)),
                Rect::new(x0 as u16, y0 as u16, 1, 1),
            );
        }

        if x0 == x1 && y0 == y1 {
            break;
        }

        let e2 = 2 * err;
        if e2 >= dy {
            if x0 == x1 {
                break;
            }
            err += dy;
            x0 += sx;
        }
        if e2 <= dx {
            if y0 == y1 {
                break;
            }
            err += dx;
            y0 += sy;
        }
        step += 1;
    }
}

fn edge_base_char(dx: i32, dy: i32) -> &'static str {
    let ax = dx.abs();
    let ay = dy.abs();
    if ax > ay * 2 {
        "-"
    } else if ay > ax * 2 {
        "|"
    } else if (dx >= 0 && dy >= 0) || (dx < 0 && dy < 0) {
        "\\"
    } else {
        "/"
    }
}

fn draw_worktree_details_panel(frame: &mut ratatui::Frame<'_>, app: &App, area: Rect) {
    let mut lines: Vec<Line<'_>> = Vec::new();
    let root_branch = current_session_branch(app);
    let parents = worktree_parent_map(&app.worktrees, root_branch.as_str());

    if let Some(selected) = app.selected_worktree() {
        lines.push(Line::from(vec![
            Span::styled("branch: ", Style::default().fg(Color::Gray)),
            Span::styled(selected.branch.as_str(), Style::default().fg(Color::Cyan)),
        ]));
        lines.push(Line::from(vec![
            Span::styled("path:   ", Style::default().fg(Color::Gray)),
            Span::styled(selected.path.as_str(), Style::default().fg(Color::White)),
        ]));
        lines.push(Line::from(vec![
            Span::styled("head:   ", Style::default().fg(Color::Gray)),
            Span::styled(
                selected.head.as_str(),
                Style::default().fg(Color::LightBlue),
            ),
        ]));
        lines.push(Line::from(vec![
            Span::styled("source: ", Style::default().fg(Color::Gray)),
            Span::styled(
                worktree_parent_label(app, &parents),
                Style::default().fg(Color::LightMagenta),
            ),
        ]));
        lines.push(Line::from(""));

        lines.push(Line::from(vec![
            Span::styled("dirty:  ", Style::default().fg(Color::Gray)),
            Span::styled(
                if selected.dirty { "yes" } else { "no" },
                Style::default().fg(if selected.dirty {
                    Color::Yellow
                } else {
                    Color::Green
                }),
            ),
            Span::raw("   "),
            Span::styled("locked: ", Style::default().fg(Color::Gray)),
            Span::styled(
                if selected.locked { "yes" } else { "no" },
                Style::default().fg(if selected.locked {
                    Color::Yellow
                } else {
                    Color::Green
                }),
            ),
        ]));

        lines.push(Line::from(vec![
            Span::styled("ahead:  ", Style::default().fg(Color::Gray)),
            Span::styled(
                selected.ahead.to_string(),
                Style::default().fg(Color::Green),
            ),
            Span::raw("   "),
            Span::styled("behind: ", Style::default().fg(Color::Gray)),
            Span::styled(
                selected.behind.to_string(),
                Style::default().fg(Color::Yellow),
            ),
        ]));

        lines.push(Line::from(vec![
            Span::styled("flags:  ", Style::default().fg(Color::Gray)),
            Span::styled(
                worktree_flags(selected),
                Style::default().fg(Color::LightMagenta),
            ),
        ]));
        lines.push(Line::from(""));
        let status_max = area.width.saturating_sub(4) as usize;
        let status_text = sanitize_for_tui(app.status_line.as_str());
        let inner_height = area.height.saturating_sub(2) as usize;
        let status_max_lines = inner_height.saturating_sub(lines.len() + 1).max(1);
        lines.push(Line::from(vec![Span::styled(
            "status:",
            Style::default().fg(Color::Gray),
        )]));
        for wrapped in wrap_text_lines(status_text.as_str(), status_max.max(12), status_max_lines) {
            lines.push(Line::from(vec![Span::styled(
                wrapped,
                Style::default().fg(Color::White),
            )]));
        }
    } else {
        lines.push(Line::from("No worktree selected"));
    }

    let border_color = if app.worktree_focus == WorktreePane::Details {
        Color::Cyan
    } else {
        Color::Gray
    };

    let panel = Paragraph::new(lines)
        .block(
            Block::default()
                .title("details [?]")
                .borders(Borders::ALL)
                .border_style(Style::default().fg(border_color))
                .style(Style::default().bg(Color::Black)),
        )
        .style(Style::default().bg(Color::Black).fg(Color::White))
        .alignment(Alignment::Left);

    frame.render_widget(panel, area);
}

fn draw_worktree_actions_panel(frame: &mut ratatui::Frame<'_>, app: &App, area: Rect) {
    let border_color = if app.worktree_focus == WorktreePane::Actions {
        Color::Cyan
    } else {
        Color::Gray
    };

    let lines = vec![
        Line::from(vec![
            Span::styled("w", Style::default().fg(Color::LightBlue)),
            Span::raw(" file changes view"),
        ]),
        Line::from(vec![
            Span::styled("r", Style::default().fg(Color::Cyan)),
            Span::raw(" refresh worktrees"),
        ]),
        Line::from(vec![
            Span::styled("q", Style::default().fg(Color::Red)),
            Span::raw(" quit"),
        ]),
        Line::from(""),
        Line::from(vec![
            Span::styled("a", Style::default().fg(Color::LightGreen)),
            Span::raw(" create worktree"),
        ]),
        Line::from(vec![
            Span::styled("o", Style::default().fg(Color::LightBlue)),
            Span::raw(" open terminal popup"),
        ]),
        Line::from(vec![
            Span::styled("z", Style::default().fg(Color::LightBlue)),
            Span::raw(" open terminal popup"),
        ]),
        Line::from(vec![
            Span::styled("f", Style::default().fg(Color::Cyan)),
            Span::raw(" fetch selected"),
        ]),
        Line::from(vec![
            Span::styled("p", Style::default().fg(Color::Magenta)),
            Span::raw(" pull selected"),
        ]),
        Line::from(vec![
            Span::styled("d", Style::default().fg(Color::LightRed)),
            Span::raw(" delete selected"),
        ]),
        Line::from(vec![
            Span::styled("m", Style::default().fg(Color::LightGreen)),
            Span::raw(" merge to parent"),
        ]),
        Line::from(vec![
            Span::styled("u", Style::default().fg(Color::Cyan)),
            Span::raw(" update parent"),
        ]),
        Line::from(vec![
            Span::styled("P", Style::default().fg(Color::LightMagenta)),
            Span::raw(" add+commit+push"),
        ]),
        Line::from(vec![
            Span::styled("x", Style::default().fg(Color::Yellow)),
            Span::raw(" prune stale"),
        ]),
        Line::from(""),
        Line::from(vec![
            Span::styled("tab", Style::default().fg(Color::LightBlue)),
            Span::raw(" switch panel"),
        ]),
        Line::from(vec![
            Span::styled("?", Style::default().fg(Color::Yellow)),
            Span::raw(" panel help"),
        ]),
        Line::from(vec![
            Span::styled("arrows", Style::default().fg(Color::LightBlue)),
            Span::raw(" move on canvas"),
        ]),
        Line::from(vec![
            Span::styled("h/l", Style::default().fg(Color::LightBlue)),
            Span::raw(" left/right in level"),
        ]),
        Line::from(vec![
            Span::styled("j/k", Style::default().fg(Color::LightBlue)),
            Span::raw(" child/parent level"),
        ]),
    ];

    frame.render_widget(
        Paragraph::new(lines)
            .block(
                Block::default()
                    .title("actions [?]")
                    .borders(Borders::ALL)
                    .border_style(Style::default().fg(border_color))
                    .style(Style::default().bg(Color::Black)),
            )
            .style(Style::default().fg(Color::White)),
        area,
    );
}

fn draw_worktree_help_modal(frame: &mut ratatui::Frame<'_>, app: &App) {
    let popup = centered_rect(64, 42, frame.area());
    frame.render_widget(Clear, popup);

    let lines = worktree_help_lines(app.worktree_focus);
    let panel = Paragraph::new(lines)
        .block(
            Block::default()
                .title("Panel Help")
                .borders(Borders::ALL)
                .border_style(Style::default().fg(Color::Yellow))
                .style(Style::default().bg(Color::Black)),
        )
        .style(Style::default().fg(Color::White));

    frame.render_widget(panel, popup);
}

fn worktree_help_lines(pane: WorktreePane) -> Vec<Line<'static>> {
    match pane {
        WorktreePane::Canvas => vec![
            Line::from("Canvas panel"),
            Line::from("- Graph root is HEAD (<branch>)"),
            Line::from("- Dotted edges show inferred branch parent links"),
            Line::from("- Arrow keys: move by direction with wrap across graph rows"),
            Line::from("- h/l: move left/right among siblings at this level"),
            Line::from("- j/k: move child/parent by graph level"),
            Line::from("- Selected node controls details/actions"),
            Line::from("- tab: move focus to next panel"),
            Line::from("- ?: close this help"),
        ],
        WorktreePane::Details => vec![
            Line::from("Details panel"),
            Line::from("- Shows branch/path/head and repo flags"),
            Line::from("- Shows ahead/behind and dirty/locked state"),
            Line::from("- Reflects current canvas selection"),
            Line::from("- tab: move focus to next panel"),
            Line::from("- ?: close this help"),
        ],
        WorktreePane::Actions => vec![
            Line::from("Actions panel"),
            Line::from("- a: create worktree from branch name"),
            Line::from("- o: open/reopen terminal popup for selected node"),
            Line::from("- z: same as o (open/reopen terminal popup)"),
            Line::from("- terminal popup: Ctrl+G toggles INPUT/CONTROL shortcuts"),
            Line::from("- f: fetch selected worktree"),
            Line::from("- p: pull selected worktree"),
            Line::from("- d: delete selected worktree (safe checks)"),
            Line::from("- m: merge selected branch into connected parent node"),
            Line::from("- u: fetch+pull connected parent node before merge"),
            Line::from("- P: selected worktree add+commit+push with message popup"),
            Line::from("- x: prune stale worktrees"),
            Line::from("- ?: close this help"),
        ],
    }
}

fn draw_worktree_create_modal(frame: &mut ratatui::Frame<'_>, app: &App) {
    let popup = centered_rect(74, 30, frame.area());
    frame.render_widget(Clear, popup);

    let border = Block::default()
        .title("Create Worktree")
        .borders(Borders::ALL)
        .style(Style::default().bg(Color::Black))
        .border_style(Style::default().fg(Color::LightGreen));
    frame.render_widget(border, popup);

    let layout = Layout::default()
        .direction(Direction::Vertical)
        .margin(1)
        .constraints([
            Constraint::Length(2),
            Constraint::Length(3),
            Constraint::Length(3),
            Constraint::Length(1),
        ])
        .split(popup);

    frame.render_widget(
        Paragraph::new(
            "Choose source above, then type worktree branch. Enter creates '.gitfetch-worktrees/<branch>'",
        )
            .style(Style::default().fg(Color::Gray)),
        layout[0],
    );

    frame.render_widget(
        Paragraph::new(Line::from(vec![
            Span::styled("Base: ", Style::default().fg(Color::Gray)),
            Span::styled(
                worktree_create_base_label(app.new_worktree_base),
                Style::default().fg(Color::LightGreen),
            ),
            Span::raw("  (use ←/→)"),
        ]))
        .block(Block::default().title("Source").borders(Borders::ALL))
        .style(Style::default().fg(Color::White)),
        layout[1],
    );

    frame.render_widget(
        Paragraph::new(app.new_worktree_branch.as_str())
            .block(Block::default().title("Branch").borders(Borders::ALL))
            .style(Style::default().fg(Color::Cyan)),
        layout[2],
    );

    frame.render_widget(
        Paragraph::new("Esc cancels")
            .alignment(Alignment::Center)
            .style(Style::default().fg(Color::Gray)),
        layout[3],
    );
}

fn draw_agent_popup(frame: &mut ratatui::Frame<'_>, app: &App) {
    let popup = terminal_popup_rect(frame.area());
    frame.render_widget(Clear, popup);

    let border = Block::default()
        .title("Terminal Session")
        .borders(Borders::ALL)
        .style(Style::default().bg(Color::Black))
        .border_style(Style::default().fg(Color::Cyan));
    frame.render_widget(border, popup);

    let layout = Layout::default()
        .direction(Direction::Vertical)
        .margin(1)
        .constraints([
            Constraint::Length(1),
            Constraint::Length(3),
            Constraint::Min(8),
            Constraint::Length(1),
        ])
        .split(popup);

    let path = app
        .agent_popup_path
        .as_deref()
        .unwrap_or("(no worktree selected)");
    let state = agent_state_for_path(app, path);
    frame.render_widget(
        Paragraph::new(Line::from(vec![
            Span::styled("worktree: ", Style::default().fg(Color::Gray)),
            Span::styled(path, Style::default().fg(Color::White)),
            Span::raw("   "),
            Span::styled("terminal: ", Style::default().fg(Color::Gray)),
            Span::styled("shell", Style::default().fg(Color::LightCyan)),
            Span::raw("   "),
            Span::styled("mode: ", Style::default().fg(Color::Gray)),
            Span::styled(
                terminal_popup_mode_text(app.terminal_popup_mode),
                terminal_popup_mode_style(app.terminal_popup_mode),
            ),
            Span::raw("   "),
            Span::styled("status: ", Style::default().fg(Color::Gray)),
            Span::styled(agent_state_text(state), agent_state_style(state)),
        ])),
        layout[0],
    );

    let mut lines: Vec<Line<'_>> = Vec::new();
    if let Some(session) = app.agent_sessions.get(path) {
        let visible_rows = layout[2].height.saturating_sub(2) as usize;
        let width = layout[2].width.saturating_sub(2).max(1);
        lines = render_terminal_lines(session, width, visible_rows);
    }
    if lines.is_empty() {
        lines.push(Line::from("(terminal booting...)"));
    }

    frame.render_widget(
        Paragraph::new(lines)
            .block(Block::default().title("Terminal").borders(Borders::ALL))
            .style(Style::default().fg(Color::White)),
        layout[2],
    );
    frame.render_widget(
        Paragraph::new(terminal_footer_text(app.terminal_popup_mode))
            .style(Style::default().fg(Color::Gray)),
        layout[3],
    );
}

fn terminal_popup_mode_text(mode: TerminalPopupMode) -> &'static str {
    match mode {
        TerminalPopupMode::Input => "INPUT",
        TerminalPopupMode::Control => "CONTROL",
    }
}

fn terminal_popup_mode_style(mode: TerminalPopupMode) -> Style {
    match mode {
        TerminalPopupMode::Input => Style::default().fg(Color::LightGreen),
        TerminalPopupMode::Control => Style::default().fg(Color::LightYellow),
    }
}

fn terminal_footer_text(mode: TerminalPopupMode) -> &'static str {
    match mode {
        TerminalPopupMode::Input => {
            "INPUT mode: typing goes to terminal. Ctrl+G switches to CONTROL mode."
        }
        TerminalPopupMode::Control => {
            "CONTROL mode: Esc background, q quit session, r restart, i return INPUT."
        }
    }
}

fn agent_state_for_path(app: &App, path: &str) -> AgentState {
    app.agent_sessions
        .get(path)
        .map(|s| s.state)
        .unwrap_or(AgentState::Launching)
}

fn agent_state_text(state: AgentState) -> &'static str {
    match state {
        AgentState::Launching => "loading",
        AgentState::Running => "running",
        AgentState::Done => "done",
        AgentState::Failed => "failed",
    }
}

fn agent_state_style(state: AgentState) -> Style {
    match state {
        AgentState::Launching => Style::default().fg(Color::Yellow),
        AgentState::Running => Style::default().fg(Color::LightCyan),
        AgentState::Done => Style::default().fg(Color::Green),
        AgentState::Failed => Style::default().fg(Color::Red),
    }
}

fn render_terminal_lines(
    session: &AgentSession,
    width: u16,
    visible_rows: usize,
) -> Vec<Line<'static>> {
    if width == 0 || visible_rows == 0 {
        return Vec::new();
    }

    let screen = session.parser.screen();
    let (rows, cols) = screen.size();
    let cols = cols.min(width);
    let start_row = rows.saturating_sub(visible_rows as u16);
    let mut out = Vec::new();

    for row in start_row..rows {
        let mut spans: Vec<Span<'static>> = Vec::new();
        let mut run = String::new();
        let mut run_style: Option<Style> = None;

        for col in 0..cols {
            let Some(cell) = screen.cell(row, col) else {
                continue;
            };
            if cell.is_wide_continuation() {
                continue;
            }
            let style = vt_cell_style(cell);
            let mut text = cell.contents();
            if text.is_empty() {
                text.push(' ');
            }

            match run_style {
                Some(existing) if existing == style => {
                    run.push_str(text.as_str());
                }
                _ => {
                    if !run.is_empty() {
                        let taken = std::mem::take(&mut run);
                        spans.push(Span::styled(taken, run_style.unwrap_or_default()));
                    }
                    run_style = Some(style);
                    run.push_str(text.as_str());
                }
            }
        }

        if !run.is_empty() {
            spans.push(Span::styled(run, run_style.unwrap_or_default()));
        }

        if spans.is_empty() {
            out.push(Line::from(""));
        } else {
            out.push(Line::from(spans));
        }
    }

    out
}

fn vt_cell_style(cell: &vt100::Cell) -> Style {
    let mut style = Style::default();
    style = style.fg(vt_color_to_ratatui(cell.fgcolor(), true));
    style = style.bg(vt_color_to_ratatui(cell.bgcolor(), false));
    if cell.bold() {
        style = style.add_modifier(Modifier::BOLD);
    }
    if cell.italic() {
        style = style.add_modifier(Modifier::ITALIC);
    }
    if cell.underline() {
        style = style.add_modifier(Modifier::UNDERLINED);
    }
    style
}

fn vt_color_to_ratatui(color: vt100::Color, is_fg: bool) -> Color {
    match color {
        vt100::Color::Default => {
            if is_fg {
                Color::White
            } else {
                Color::Black
            }
        }
        vt100::Color::Rgb(r, g, b) => Color::Rgb(r, g, b),
        vt100::Color::Idx(i) => ansi_idx_to_color(i),
    }
}

fn ansi_idx_to_color(i: u8) -> Color {
    match i {
        0 => Color::Black,
        1 => Color::Red,
        2 => Color::Green,
        3 => Color::Yellow,
        4 => Color::Blue,
        5 => Color::Magenta,
        6 => Color::Cyan,
        7 => Color::Gray,
        8 => Color::DarkGray,
        9 => Color::LightRed,
        10 => Color::LightGreen,
        11 => Color::LightYellow,
        12 => Color::LightBlue,
        13 => Color::LightMagenta,
        14 => Color::LightCyan,
        15 => Color::White,
        16..=231 => {
            let idx = i - 16;
            let r = idx / 36;
            let g = (idx % 36) / 6;
            let b = idx % 6;
            let scale = [0, 95, 135, 175, 215, 255];
            Color::Rgb(scale[r as usize], scale[g as usize], scale[b as usize])
        }
        232..=255 => {
            let shade = 8 + (i - 232) * 10;
            Color::Rgb(shade, shade, shade)
        }
    }
}

fn draw_branch_conflict_confirm_modal(frame: &mut ratatui::Frame<'_>, app: &App) {
    let popup = centered_rect(72, 26, frame.area());
    frame.render_widget(Clear, popup);

    let border = Block::default()
        .title("Branch Exists")
        .borders(Borders::ALL)
        .style(Style::default().bg(Color::Black))
        .border_style(Style::default().fg(Color::LightRed));
    frame.render_widget(border, popup);

    let layout = Layout::default()
        .direction(Direction::Vertical)
        .margin(1)
        .constraints([
            Constraint::Length(2),
            Constraint::Length(2),
            Constraint::Length(3),
            Constraint::Length(1),
        ])
        .split(popup);

    let branch = if app.pending_create_branch.is_empty() {
        app.new_worktree_branch.as_str()
    } else {
        app.pending_create_branch.as_str()
    };

    frame.render_widget(
        Paragraph::new(format!(
            "Branch '{}' already exists. Delete and create new worktree?",
            branch
        ))
        .style(Style::default().fg(Color::White)),
        layout[0],
    );

    frame.render_widget(
        Paragraph::new(
            "Default selection is No. Use ←/→ (or y/n), Enter to confirm, Esc to cancel.",
        )
        .style(Style::default().fg(Color::Gray)),
        layout[1],
    );

    let yes_style = if app.confirm_delete_branch_yes {
        Style::default().fg(Color::Black).bg(Color::LightRed)
    } else {
        Style::default().fg(Color::White)
    };
    let no_style = if app.confirm_delete_branch_yes {
        Style::default().fg(Color::White)
    } else {
        Style::default().fg(Color::Black).bg(Color::LightGreen)
    };

    frame.render_widget(
        Paragraph::new(Line::from(vec![
            Span::styled("[ Yes: delete + recreate ]", yes_style),
            Span::raw("   "),
            Span::styled("[ No: keep branch ]", no_style),
        ]))
        .alignment(Alignment::Center),
        layout[2],
    );

    frame.render_widget(
        Paragraph::new("No is selected by default")
            .alignment(Alignment::Center)
            .style(Style::default().fg(Color::Gray)),
        layout[3],
    );
}

fn draw_quit_with_sessions_modal(frame: &mut ratatui::Frame<'_>, app: &App) {
    let popup = centered_rect(68, 26, frame.area());
    frame.render_widget(Clear, popup);

    let border = Block::default()
        .title("Active Sessions")
        .borders(Borders::ALL)
        .style(Style::default().bg(Color::Black))
        .border_style(Style::default().fg(Color::LightRed));
    frame.render_widget(border, popup);

    let layout = Layout::default()
        .direction(Direction::Vertical)
        .margin(1)
        .constraints([
            Constraint::Length(2),
            Constraint::Length(2),
            Constraint::Length(3),
            Constraint::Length(1),
        ])
        .split(popup);

    let count = live_terminal_session_count(app);
    frame.render_widget(
        Paragraph::new(format!(
            "You have {} active terminal session(s). Quit anyway?",
            count
        ))
        .style(Style::default().fg(Color::White)),
        layout[0],
    );

    frame.render_widget(
        Paragraph::new("Choosing Yes will close the TUI and terminate those PTY sessions.")
            .style(Style::default().fg(Color::Gray)),
        layout[1],
    );

    let yes_style = if app.confirm_quit_with_sessions_yes {
        Style::default().fg(Color::Black).bg(Color::LightRed)
    } else {
        Style::default().fg(Color::White)
    };
    let no_style = if app.confirm_quit_with_sessions_yes {
        Style::default().fg(Color::White)
    } else {
        Style::default().fg(Color::Black).bg(Color::LightGreen)
    };

    frame.render_widget(
        Paragraph::new(Line::from(vec![
            Span::styled("[ Yes: quit ]", yes_style),
            Span::raw("   "),
            Span::styled("[ No: stay ]", no_style),
        ]))
        .alignment(Alignment::Center),
        layout[2],
    );

    frame.render_widget(
        Paragraph::new("No is selected by default")
            .alignment(Alignment::Center)
            .style(Style::default().fg(Color::Gray)),
        layout[3],
    );
}

fn worktree_create_base_label(base: WorktreeCreateBase) -> &'static str {
    match base {
        WorktreeCreateBase::Main => "main branch",
        WorktreeCreateBase::Selected => "selected branch/worktree",
        WorktreeCreateBase::SelectedWithChanges => "selected branch/worktree + uncommitted changes",
    }
}

fn worktree_flags(entry: &WorktreeEntry) -> String {
    let mut flags: Vec<&str> = Vec::new();
    if entry.is_current {
        flags.push("current");
    }
    if entry.detached {
        flags.push("detached");
    }
    if entry.bare {
        flags.push("bare");
    }
    if entry.locked {
        flags.push("locked");
    }
    if entry.prunable {
        flags.push("prunable");
    }

    if flags.is_empty() {
        "none".to_string()
    } else {
        flags.join(", ")
    }
}

fn build_tree_items(files: &[FileEntry]) -> Vec<TreeItem> {
    let mut file_status: BTreeMap<String, PathStatus> = BTreeMap::new();
    let mut folder_status: BTreeMap<String, PathStatus> = BTreeMap::new();
    let mut file_delta = collect_file_deltas(files);
    let mut folder_delta: BTreeMap<String, PathDelta> = BTreeMap::new();

    for file in files {
        let status = PathStatus {
            staged: file.staged,
            unstaged: file.unstaged,
            untracked: file.untracked,
        };
        file_status.insert(file.path.clone(), status);

        if file.untracked {
            let added = fs::read_to_string(&file.path)
                .map(|text| text.lines().count())
                .unwrap_or(0);
            file_delta
                .entry(file.path.clone())
                .and_modify(|d| d.added_lines = d.added_lines.max(added))
                .or_insert(PathDelta {
                    added_lines: added,
                    removed_lines: 0,
                });
        }

        let mut parts: Vec<&str> = file.path.split('/').collect();
        let _ = parts.pop();
        for depth in 0..parts.len() {
            let folder_path = parts[..=depth].join("/");
            merge_status(&mut folder_status, folder_path, status);
        }
    }

    for (path, delta) in &file_delta {
        let mut parts: Vec<&str> = path.split('/').collect();
        let _ = parts.pop();
        for depth in 0..parts.len() {
            let folder_path = parts[..=depth].join("/");
            merge_delta(&mut folder_delta, folder_path, *delta);
        }
    }

    let mut root = TreeNode::default();
    for path in file_status.keys() {
        insert_path_into_tree(&mut root, path);
    }

    let mut items = Vec::new();
    flatten_tree(
        &root,
        "",
        0,
        &folder_status,
        &file_status,
        &folder_delta,
        &file_delta,
        &mut items,
    );
    items
}

fn collect_file_deltas(files: &[FileEntry]) -> BTreeMap<String, PathDelta> {
    let mut deltas: BTreeMap<String, PathDelta> = BTreeMap::new();

    if let Some(numstat) = git_output(&["diff", "--numstat", "HEAD"]) {
        for line in numstat.lines() {
            let mut parts = line.split('\t');
            let added_raw = parts.next().unwrap_or_default();
            let removed_raw = parts.next().unwrap_or_default();
            let path = parts.next().unwrap_or_default().trim();
            if path.is_empty() {
                continue;
            }

            let added = added_raw.parse::<usize>().unwrap_or(0);
            let removed = removed_raw.parse::<usize>().unwrap_or(0);
            deltas.insert(
                path.to_string(),
                PathDelta {
                    added_lines: added,
                    removed_lines: removed,
                },
            );
        }
    }

    for file in files {
        deltas.entry(file.path.clone()).or_default();
    }

    deltas
}

#[derive(Default)]
struct TreeNode {
    children: BTreeMap<String, TreeNode>,
    is_file: bool,
}

fn insert_path_into_tree(root: &mut TreeNode, path: &str) {
    let mut current = root;
    let parts: Vec<&str> = path.split('/').collect();

    for (idx, part) in parts.iter().enumerate() {
        let node = current.children.entry((*part).to_string()).or_default();
        if idx == parts.len() - 1 {
            node.is_file = true;
        }
        current = node;
    }
}

fn flatten_tree(
    node: &TreeNode,
    parent_path: &str,
    depth: usize,
    folder_status: &BTreeMap<String, PathStatus>,
    file_status: &BTreeMap<String, PathStatus>,
    folder_delta: &BTreeMap<String, PathDelta>,
    file_delta: &BTreeMap<String, PathDelta>,
    out: &mut Vec<TreeItem>,
) {
    let mut entries: Vec<(&String, &TreeNode)> = node.children.iter().collect();
    entries.sort_by(
        |(a_name, a_node), (b_name, b_node)| match (a_node.is_file, b_node.is_file) {
            (false, true) => std::cmp::Ordering::Less,
            (true, false) => std::cmp::Ordering::Greater,
            _ => a_name.cmp(b_name),
        },
    );

    for (name, child) in entries.into_iter() {
        let path = if parent_path.is_empty() {
            (*name).to_string()
        } else {
            format!("{}/{}", parent_path, name)
        };

        if child.is_file {
            let status = *file_status.get(&path).unwrap_or(&PathStatus::default());
            let delta = *file_delta.get(&path).unwrap_or(&PathDelta::default());
            out.push(TreeItem {
                path: path.clone(),
                label: format!("{}{}", "  ".repeat(depth), name),
                kind: TreeKind::File,
                staged: status.staged,
                unstaged: status.unstaged,
                untracked: status.untracked,
                added_lines: delta.added_lines,
                removed_lines: delta.removed_lines,
            });
        } else {
            let status = *folder_status.get(&path).unwrap_or(&PathStatus::default());
            let delta = *folder_delta.get(&path).unwrap_or(&PathDelta::default());
            out.push(TreeItem {
                path: path.clone(),
                label: format!("{}{}/", "  ".repeat(depth), name),
                kind: TreeKind::Folder,
                staged: status.staged,
                unstaged: status.unstaged,
                untracked: status.untracked,
                added_lines: delta.added_lines,
                removed_lines: delta.removed_lines,
            });
        }

        flatten_tree(
            child,
            &path,
            depth + 1,
            folder_status,
            file_status,
            folder_delta,
            file_delta,
            out,
        );
    }
}

fn merge_status(store: &mut BTreeMap<String, PathStatus>, key: String, status: PathStatus) {
    let entry = store.entry(key).or_default();
    entry.staged |= status.staged;
    entry.unstaged |= status.unstaged;
    entry.untracked |= status.untracked;
}

fn merge_delta(store: &mut BTreeMap<String, PathDelta>, key: String, delta: PathDelta) {
    let entry = store.entry(key).or_default();
    entry.added_lines += delta.added_lines;
    entry.removed_lines += delta.removed_lines;
}

fn max_overview_scroll(app: &App) -> u16 {
    let lines = overview_line_count(app.selected_overview.as_ref());
    let visible = 22usize;
    lines.saturating_sub(visible) as u16
}

fn overview_line_count(info: Option<&FileOverview>) -> usize {
    let Some(info) = info else {
        return 1;
    };

    let mut count = 6usize;
    if info.use_traditional_overview {
        count += 2 + info.traditional_diff.len().min(24);
    } else {
        count += 1 + info.methods_added.len().min(8);
        count += 1 + info.methods_modified.len().min(8);
        count += 1 + info.methods_deleted.len().min(8);
    }
    count
}

fn should_hide_internal_worktree_path(path: &str) -> bool {
    if !path.starts_with(".gitfetch-worktrees/") {
        return false;
    }

    path != ".gitfetch-worktrees/.parent-hints"
}

fn truncate_text(text: &str, max_chars: usize) -> String {
    if max_chars == 0 {
        return String::new();
    }

    let total = text.chars().count();
    if total <= max_chars {
        return text.to_string();
    }

    if max_chars <= 3 {
        return ".".repeat(max_chars);
    }

    let mut out = String::new();
    for (idx, ch) in text.chars().enumerate() {
        if idx >= max_chars - 3 {
            out.push_str("...");
            return out;
        }
        out.push(ch);
    }
    out
}

fn single_line(text: &str) -> String {
    text.lines().next().unwrap_or_default().trim().to_string()
}

fn wrap_text_lines(text: &str, max_chars: usize, max_lines: usize) -> Vec<String> {
    if max_chars == 0 || max_lines == 0 {
        return vec![String::new()];
    }

    let mut out: Vec<String> = Vec::new();
    for raw_line in text.lines() {
        let words: Vec<&str> = raw_line.split_whitespace().collect();
        if words.is_empty() {
            out.push(String::new());
            if out.len() >= max_lines {
                return out;
            }
            continue;
        }

        let mut current = String::new();
        for word in words {
            let candidate = if current.is_empty() {
                word.to_string()
            } else {
                format!("{} {}", current, word)
            };

            if candidate.chars().count() <= max_chars {
                current = candidate;
                continue;
            }

            if !current.is_empty() {
                out.push(current);
                if out.len() >= max_lines {
                    return out;
                }
                current = String::new();
            }

            if word.chars().count() <= max_chars {
                current = word.to_string();
            } else {
                for segment in split_text_chunks(word, max_chars) {
                    out.push(segment);
                    if out.len() >= max_lines {
                        return out;
                    }
                }
            }
        }

        if !current.is_empty() {
            out.push(current);
            if out.len() >= max_lines {
                return out;
            }
        }
    }

    if out.is_empty() {
        out.push(String::new());
    }

    out
}

fn split_text_chunks(text: &str, chunk_size: usize) -> Vec<String> {
    if chunk_size == 0 {
        return vec![String::new()];
    }

    let mut out = Vec::new();
    let mut current = String::new();
    let mut count = 0usize;
    for ch in text.chars() {
        if count >= chunk_size {
            out.push(current);
            current = String::new();
            count = 0;
        }
        current.push(ch);
        count += 1;
    }
    if !current.is_empty() {
        out.push(current);
    }
    if out.is_empty() {
        out.push(String::new());
    }
    out
}

fn draw_commit_modal(frame: &mut ratatui::Frame<'_>, app: &App) {
    let popup = centered_rect(70, 22, frame.area());
    frame.render_widget(Clear, popup);

    let border = Block::default()
        .title("Create Commit")
        .borders(Borders::ALL)
        .style(Style::default().bg(Color::Black))
        .border_style(Style::default().fg(Color::Yellow));
    frame.render_widget(border, popup);

    let layout = Layout::default()
        .direction(Direction::Vertical)
        .margin(1)
        .constraints([
            Constraint::Length(1),
            Constraint::Min(1),
            Constraint::Length(1),
        ])
        .split(popup);

    frame.render_widget(
        Paragraph::new("Write commit message and press Enter")
            .alignment(Alignment::Center)
            .style(
                Style::default()
                    .fg(Color::White)
                    .add_modifier(Modifier::BOLD),
            ),
        layout[0],
    );

    frame.render_widget(
        Paragraph::new(app.commit_input.as_str())
            .block(Block::default().title("Message").borders(Borders::ALL))
            .style(Style::default().fg(Color::Cyan)),
        layout[1],
    );

    frame.render_widget(
        Paragraph::new("Esc cancels")
            .alignment(Alignment::Center)
            .style(Style::default().fg(Color::Gray)),
        layout[2],
    );
}

fn draw_worktree_commit_push_modal(frame: &mut ratatui::Frame<'_>, app: &App) {
    let popup = centered_rect(74, 26, frame.area());
    frame.render_widget(Clear, popup);

    let border = Block::default()
        .title("Worktree Commit+Push")
        .borders(Borders::ALL)
        .style(Style::default().bg(Color::Black))
        .border_style(Style::default().fg(Color::LightGreen));
    frame.render_widget(border, popup);

    let layout = Layout::default()
        .direction(Direction::Vertical)
        .margin(1)
        .constraints([
            Constraint::Length(1),
            Constraint::Length(1),
            Constraint::Min(1),
            Constraint::Length(1),
        ])
        .split(popup);

    let path = app
        .worktree_commit_path
        .as_deref()
        .map(|p| truncate_text(p, 62))
        .unwrap_or_else(|| "(no selected worktree)".to_string());

    frame.render_widget(
        Paragraph::new(format!("Target: {}", path))
            .alignment(Alignment::Left)
            .style(Style::default().fg(Color::Gray)),
        layout[0],
    );

    frame.render_widget(
        Paragraph::new("Enter message, then Enter runs: git add . -> git commit -m -> git push")
            .alignment(Alignment::Left)
            .style(Style::default().fg(Color::White)),
        layout[1],
    );

    frame.render_widget(
        Paragraph::new(app.worktree_commit_input.as_str())
            .block(Block::default().title("Message").borders(Borders::ALL))
            .style(Style::default().fg(Color::Cyan)),
        layout[2],
    );

    frame.render_widget(
        Paragraph::new("Esc cancels")
            .alignment(Alignment::Center)
            .style(Style::default().fg(Color::Gray)),
        layout[3],
    );
}

fn centered_rect(percent_x: u16, percent_y: u16, area: Rect) -> Rect {
    let vertical = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Percentage((100 - percent_y) / 2),
            Constraint::Percentage(percent_y),
            Constraint::Percentage((100 - percent_y) / 2),
        ])
        .split(area);

    Layout::default()
        .direction(Direction::Horizontal)
        .constraints([
            Constraint::Percentage((100 - percent_x) / 2),
            Constraint::Percentage(percent_x),
            Constraint::Percentage((100 - percent_x) / 2),
        ])
        .split(vertical[1])[1]
}

fn terminal_popup_rect(area: Rect) -> Rect {
    let vertical_margin = 1;
    let available_height = area.height.saturating_sub(vertical_margin * 2);

    let width = area.width.max(1);
    let height = available_height.max(1);

    let x = area.x;
    let y = area.y.saturating_add(vertical_margin);

    Rect::new(x, y, width, height)
}
