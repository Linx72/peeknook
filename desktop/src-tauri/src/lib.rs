use std::path::PathBuf;
use std::process::Command;
use std::thread;
use std::time::Duration;

use tauri_plugin_shell::ShellExt;

fn project_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../..")
        .canonicalize()
        .unwrap_or_else(|_| PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../.."))
}

fn start_backend_script() {
    let script = project_root().join("scripts/peeknook-backend.sh");
    if !script.exists() {
        eprintln!("PeekNook backend script not found: {}", script.display());
        return;
    }
    let _ = Command::new("bash").arg(script).spawn();
    thread::sleep(Duration::from_secs(2));
}

fn start_backend(app: &tauri::App) {
    let sidecar = app
        .shell()
        .sidecar("peeknook-api")
        .map(|cmd| {
            cmd.env("API_PORT", "5056")
                .env("API_RELOAD", "false")
                .env("PEEKNOOK_STANDALONE", "true")
                .env("PEEKNOOK_EMBEDDED_DB", "true")
                .env("SURREAL_URL", "ws://127.0.0.1:8001/rpc")
        });

    if let Ok(command) = sidecar {
        if command.spawn().is_ok() {
            thread::sleep(Duration::from_secs(3));
            return;
        }
    }

    start_backend_script();
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let mut builder = tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init());

    #[cfg(desktop)]
    {
        builder = builder
            .plugin(tauri_plugin_updater::Builder::new().build())
            .plugin(tauri_plugin_process::init());
    }

    builder
        .setup(|app| {
            start_backend(app);
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running PeekNook desktop");
}
