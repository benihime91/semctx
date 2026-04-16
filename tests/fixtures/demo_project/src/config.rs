// Configuration types.
// FEATURE: Demo Fixture.
pub struct AppConfig {
    pub name: String,
}

pub fn load_config() -> AppConfig {
    AppConfig {
        name: "demo".to_string(),
    }
}
