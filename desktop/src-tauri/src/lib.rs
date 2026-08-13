use std::net::TcpListener;
use std::process::Command;
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

use serde::Serialize;
use tauri::Manager;
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;
use uuid::Uuid;

const TAURI_CORS_ORIGINS: &str = "tauri://localhost,http://tauri.localhost,https://tauri.localhost";

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct BackendConnection {
    base_url: String,
    port: u16,
    surreal_port: u16,
    token: String,
}

impl BackendConnection {
    fn new() -> Self {
        let api_listener = TcpListener::bind(("127.0.0.1", 0))
            .expect("failed to reserve a loopback port for the PeekNook backend");
        let surreal_listener = TcpListener::bind(("127.0.0.1", 0))
            .expect("failed to reserve a loopback port for the PeekNook database");
        let port = api_listener
            .local_addr()
            .expect("failed to read the reserved PeekNook backend port")
            .port();
        let surreal_port = surreal_listener
            .local_addr()
            .expect("failed to read the reserved PeekNook database port")
            .port();
        drop(api_listener);
        drop(surreal_listener);

        Self {
            base_url: format!("http://127.0.0.1:{port}"),
            port,
            surreal_port,
            token: Uuid::new_v4().to_string(),
        }
    }
}

#[derive(Default)]
struct BackendProcess(Mutex<Option<CommandChild>>);

#[tauri::command]
fn get_backend_connection(connection: tauri::State<'_, BackendConnection>) -> BackendConnection {
    connection.inner().clone()
}

fn start_backend(app: &tauri::App, connection: &BackendConnection) {
    // The Vite development command starts the backend before Tauri setup runs.
    if cfg!(debug_assertions) {
        return;
    }

    let sidecar = app.shell().sidecar("peeknook-api").map(|cmd| {
        cmd.env("API_PORT", connection.port.to_string())
            .env("API_RELOAD", "false")
            .env("PEEKNOOK_STANDALONE", "true")
            .env("PEEKNOOK_EMBEDDED_DB", "true")
            .env("PEEKNOOK_SURREAL_PORT", connection.surreal_port.to_string())
            .env(
                "SURREAL_URL",
                format!("ws://127.0.0.1:{}/rpc", connection.surreal_port),
            )
            .env("OPEN_NOTEBOOK_PASSWORD", &connection.token)
            .env("CORS_ORIGINS", TAURI_CORS_ORIGINS)
    });

    match sidecar {
        Ok(command) => match command.spawn() {
            Ok((_events, child)) => {
                if let Ok(mut process) = app.state::<BackendProcess>().0.lock() {
                    *process = Some(child);
                }
                thread::sleep(Duration::from_secs(3));
            }
            Err(error) => {
                eprintln!("Failed to spawn the packaged PeekNook backend: {error}");
            }
        },
        Err(error) => {
            eprintln!("Failed to resolve the packaged PeekNook backend: {error}");
        }
    }
}

#[cfg(unix)]
fn descendant_pids(root_pid: u32) -> Vec<u32> {
    let Ok(output) = Command::new("ps").args(["-axo", "pid=,ppid="]).output() else {
        return Vec::new();
    };
    let process_pairs: Vec<(u32, u32)> = String::from_utf8_lossy(&output.stdout)
        .lines()
        .filter_map(|line| {
            let mut fields = line.split_whitespace();
            let pid = fields.next()?.parse().ok()?;
            let parent_pid = fields.next()?.parse().ok()?;
            Some((pid, parent_pid))
        })
        .collect();

    let mut descendants = Vec::new();
    let mut parents = vec![root_pid];
    while let Some(parent_pid) = parents.pop() {
        for (pid, candidate_parent) in &process_pairs {
            if *candidate_parent == parent_pid && !descendants.contains(pid) {
                descendants.push(*pid);
                parents.push(*pid);
            }
        }
    }
    descendants
}

#[cfg(unix)]
fn signal_process(pid: u32, signal: &str) {
    let _ = Command::new("kill")
        .args([signal, &pid.to_string()])
        .status();
}

#[cfg(unix)]
fn process_is_alive(pid: u32) -> bool {
    Command::new("kill")
        .args(["-0", &pid.to_string()])
        .status()
        .is_ok_and(|status| status.success())
}

#[cfg(unix)]
fn terminate_backend_child(child: CommandChild) {
    let root_pid = child.pid();
    let mut process_tree = descendant_pids(root_pid);
    process_tree.push(root_pid);

    // Stop leaves first so the database can flush before its API supervisor exits.
    for pid in process_tree.iter().rev() {
        signal_process(*pid, "-TERM");
    }
    for _ in 0..20 {
        if process_tree.iter().all(|pid| !process_is_alive(*pid)) {
            break;
        }
        thread::sleep(Duration::from_millis(250));
    }
    for pid in process_tree.iter().rev() {
        if process_is_alive(*pid) {
            signal_process(*pid, "-KILL");
        }
    }
    let _ = child.kill();
}

#[cfg(windows)]
fn terminate_backend_child(child: CommandChild) {
    let root_pid = child.pid().to_string();
    let _ = Command::new("taskkill")
        .args(["/PID", &root_pid, "/T", "/F"])
        .status();
    let _ = child.kill();
}

fn stop_backend(app: &tauri::AppHandle) {
    if let Ok(mut process) = app.state::<BackendProcess>().0.lock() {
        if let Some(child) = process.take() {
            terminate_backend_child(child);
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let backend_connection = BackendConnection::new();
    let setup_connection = backend_connection.clone();
    let mut builder = tauri::Builder::default()
        .manage(backend_connection)
        .manage(BackendProcess::default())
        .invoke_handler(tauri::generate_handler![get_backend_connection])
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init());

    #[cfg(desktop)]
    {
        builder = builder
            .plugin(tauri_plugin_updater::Builder::new().build())
            .plugin(tauri_plugin_process::init());
    }

    let app = builder
        .setup(move |app| {
            start_backend(app, &setup_connection);
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building PeekNook desktop");

    app.run(|app_handle, event| {
        if matches!(event, tauri::RunEvent::Exit) {
            stop_backend(app_handle);
        }
    });
}
