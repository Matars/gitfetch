use std::error::Error;
use std::io;
use std::process::Command;
use std::time::{Duration, Instant};
use std::{
    collections::{BTreeMap, HashSet},
    fs,
};

use crossterm::event::{self, Event, KeyCode, KeyEventKind, KeyModifiers};
use crossterm::execute;
use crossterm::terminal::{
    disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
};
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
}

#[derive(Clone, Debug)]
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
    commit_input: String,
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
            commit_input: String::new(),
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

    let tick_rate = Duration::from_millis(700);
    let mut last_tick = Instant::now();
    let mut should_quit = false;

    while !should_quit {
        terminal.draw(|frame| draw_ui(frame, &app))?;

        let timeout = tick_rate.saturating_sub(last_tick.elapsed());
        if event::poll(timeout)? {
            if let Event::Key(key) = event::read()? {
                if key.kind == KeyEventKind::Press {
                    if key.modifiers.contains(KeyModifiers::CONTROL)
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
                    }
                }
            }
        }

        if last_tick.elapsed() >= tick_rate {
            refresh_status(&mut app);
            last_tick = Instant::now();
        }
    }

    terminal.show_cursor()?;
    Ok(())
}

fn handle_normal_mode_key(app: &mut App, code: KeyCode) -> Result<bool, Box<dyn Error>> {
    match code {
        KeyCode::Char('q') => return Ok(true),
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
        _ => {}
    }

    Ok(false)
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
}

fn parse_branch_line(app: &mut App, line: &str) {
    let branch: String;
    let mut ahead = 0usize;
    let mut behind = 0usize;

    let stripped = line.strip_prefix("## ").unwrap_or(line);
    if let Some((name, rest)) = stripped.split_once("...") {
        branch = name.trim().to_string();
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
    } else {
        branch = stripped.trim().to_string();
    }

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

fn run_git(args: &[&str]) -> Result<String, Box<dyn Error>> {
    let output = Command::new("git").args(args).output()?;
    let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();

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
    Some(String::from_utf8_lossy(&output.stdout).to_string())
}

fn push_with_upstream() -> Result<String, Box<dyn Error>> {
    let first = Command::new("git").args(["push"]).output()?;
    let first_stdout = String::from_utf8_lossy(&first.stdout).trim().to_string();
    let first_stderr = String::from_utf8_lossy(&first.stderr).trim().to_string();

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
    let second_stdout = String::from_utf8_lossy(&second.stdout).trim().to_string();
    let second_stderr = String::from_utf8_lossy(&second.stderr).trim().to_string();

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
    frame.render_widget(
        Block::default().style(Style::default().bg(Color::Black).fg(Color::White)),
        frame.area(),
    );

    let outer = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Min(1), Constraint::Length(3)])
        .split(frame.area());

    let columns = Layout::default()
        .direction(Direction::Horizontal)
        .spacing(1)
        .constraints([
            Constraint::Percentage(20),
            Constraint::Percentage(60),
            Constraint::Percentage(20),
        ])
        .split(outer[0]);

    draw_files_panel(frame, app, columns[0]);
    draw_selected_overview_panel(frame, app, columns[1]);
    draw_pulse_panel(frame, app, columns[2]);

    let footer = Paragraph::new(Line::from(vec![
        Span::styled("h/l", Style::default().fg(Color::LightBlue)),
        Span::raw(" focus  "),
        Span::styled("j/k", Style::default().fg(Color::LightBlue)),
        Span::raw(" move/scroll  "),
        Span::styled("space", Style::default().fg(Color::LightGreen)),
        Span::raw(" stage/unstage  "),
        Span::styled("c", Style::default().fg(Color::Yellow)),
        Span::raw(" commit  "),
        Span::styled("p", Style::default().fg(Color::Magenta)),
        Span::raw(" push  "),
        Span::styled("r", Style::default().fg(Color::Cyan)),
        Span::raw(" refresh  "),
        Span::styled("q", Style::default().fg(Color::Red)),
        Span::raw(" quit"),
    ]))
    .block(
        Block::default()
            .borders(Borders::ALL)
            .title("controls")
            .style(Style::default().bg(Color::Black))
            .border_style(Style::default().fg(Color::DarkGray)),
    )
    .style(Style::default().bg(Color::Black));
    frame.render_widget(footer, outer[1]);

    if matches!(app.mode, Mode::CommitInput) {
        draw_commit_modal(frame, app);
    }
}

fn draw_files_panel(frame: &mut ratatui::Frame<'_>, app: &App, area: Rect) {
    let content_width = area.width.saturating_sub(6) as usize;
    let mut items: Vec<ListItem<'_>> = Vec::new();
    let mut index_map: Vec<Option<usize>> = Vec::new();

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
) {
    let mut spans: Vec<Span<'_>> = Vec::new();
    let name_color = if item.kind == TreeKind::Folder {
        Color::LightYellow
    } else {
        Color::LightCyan
    };

    let plus_text = format!("+{:>4}", item.added_lines);
    let minus_text = format!("-{:>4}", item.removed_lines);
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

fn truncate_text(text: &str, max_chars: usize) -> String {
    let mut out = String::new();
    for (idx, ch) in text.chars().enumerate() {
        if idx >= max_chars {
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
