// App de escritorio de Tienda Eaciot — envoltorio web (wrapper).
//
// Abre la tienda (por defecto https://eaciot.com) en una ventana nativa.
// La URL se puede sobreescribir con la variable de entorno EACIOT_URL
// (útil para apuntar a un entorno de pruebas o a un dominio propio).

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let url = std::env::var("EACIOT_URL").unwrap_or_else(|_| "https://eaciot.com".to_string());

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .setup(move |app| {
            tauri::WebviewWindowBuilder::new(
                app,
                "main",
                tauri::WebviewUrl::External(url.parse().expect("EACIOT_URL inválida")),
            )
            .title("Tienda Eaciot")
            .inner_size(1200.0, 800.0)
            .min_inner_size(800.0, 600.0)
            .build()?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error al ejecutar Tienda Eaciot");
}
