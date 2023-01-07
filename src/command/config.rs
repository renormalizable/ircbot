use anyhow::Context as _;
use serde::{Deserialize, Serialize};
use std::{collections::HashMap, fs::File, io::Read, path::Path};

#[derive(Debug, Deserialize, Serialize)]
pub struct Config {
    pub command: Command,
    pub interpreter: Interpreter,
    pub router: Router,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct Command {
    pub baidu_translate: super::api::BtranConfig,
    pub google: super::api::GoogleConfig,
    pub google_translate: super::api::GtranConfig,
    pub wolfram: super::api::WolframConfig,
    #[serde(flatten)]
    pub raw: HashMap<String, Vec<String>>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct Interpreter {
    #[serde(flatten)]
    pub raw: HashMap<String, Vec<String>>,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct Router {
    #[serde(flatten)]
    pub raw: HashMap<String, Vec<(String, String, String)>>,
}

impl Config {
    pub fn load<P>(path: P) -> anyhow::Result<Self>
    where
        P: AsRef<Path>,
    {
        let mut file = File::open(path)?;
        let mut data = String::new();
        file.read_to_string(&mut data)?;

        Ok(serde_yaml::from_str(&data).context("config error")?)
    }
}
