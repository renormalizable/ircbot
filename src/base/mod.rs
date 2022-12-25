use thiserror::Error;

mod command;
mod context;
mod message;

pub use command::{
    BoxCommandObject, Command, CommandObject, CommandParser, Interpreter, LocalBoxCommandObject,
};
pub use context::{BoxContext, Collector, Context, LocalBoxContext};
pub use message::{Color, Message, MessageData, MessageText, Style};

#[derive(Error, Debug)]
pub enum Error {
    #[error("load error")]
    LoadError,
    #[error("parse error")]
    ParseError,
    #[error("substitute error")]
    SubstituteError,
    #[error("send error")]
    SendError,
    #[error("no output")]
    NoOutput,
    #[error("{0}")]
    Message(String),
    #[error(transparent)]
    Error(#[from] anyhow::Error),
}
