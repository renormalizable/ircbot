use crate::base::{Color, Command, Context, Error, Message, MessageData, MessageText, Style};

mod config;

pub mod api;
pub mod input;
pub mod language;
pub mod music;
pub mod random;
pub mod scheme;
pub mod utility;

pub use config::Config;

const USER_AGENT: &'static str = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.125 Safari/537.36";

impl<'a> MessageData<'a> {
    async fn from_request_builder(
        request_builder: reqwest::RequestBuilder,
        mime: mime::Mime,
    ) -> Result<MessageData<'a>, Error> {
        use anyhow::Context as _;
        use reqwest::header;

        let response = request_builder.send().await.context("send error")?;

        let url = response.url().as_str().to_owned();
        let mime = response
            .headers()
            .get(header::CONTENT_TYPE)
            .and_then(|x| x.to_str().ok())
            .and_then(|x| x.parse().ok())
            .unwrap_or(mime);
        let bytes = response.bytes().await.context("read error")?;

        Ok(MessageData {
            link: Some(url.into()),
            text: None,
            mime,
            data: bytes.to_vec(),
        })
    }
}
