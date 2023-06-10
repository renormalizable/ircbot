use anyhow::Context as _;
use async_trait::async_trait;
use pest_derive::Parser;
use url::Url;

use super::*;

pub use display::Display;
pub use include::Include;
pub use newline::Newline;

mod newline {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
        input = _{ ^"newline" }
    "#]
    pub struct Newline;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Newline {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            _parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            context.send_fmt("\n").await
        }
    }
}

mod include {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
        input = _{ ^"include" ~ WHITE_SPACE+ ~ url }
        url = { (!WHITE_SPACE+ ~ ANY)+ }
    "#]
    pub struct Include;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    impl Include {
        pub async fn dpaste(url: &str) -> Result<String, Error> {
            Self::raw(&format!("{url}/raw")).await
        }
        async fn pb(url: &str) -> Result<String, Error> {
            Self::raw(url).await
        }
        async fn raw(url: &str) -> Result<String, Error> {
            let text = reqwest::Client::builder()
                .user_agent(super::USER_AGENT)
                .build()
                .context("client error")?
                .get(url)
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            Ok(text)
        }
    }

    #[async_trait]
    impl Command for Include {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let url = Url::parse(*parameter.get(&Rule::url).unwrap()).context("parse error")?;
            let text = match url.host_str() {
                Some("dpaste.org") | Some("paste.mozilla.org") => {
                    Self::dpaste(url.as_str()).await?
                }
                Some("fars.ee") => Self::pb(url.as_str()).await?,
                _ => String::new(),
            };

            context.send_fmt(text).await
        }
    }
}

mod display {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
        input = _{ ^"display" ~ (":" ~ paste)? ~ WHITE_SPACE ~ content }
        paste = { (!WHITE_SPACE ~ ANY)+ }
        content = { ANY+ }
    "#]
    pub struct Display;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    impl Display {
        pub async fn dpaste(url: &str, content: &str) -> Result<String, Error> {
            let text = reqwest::Client::builder()
                .user_agent(super::USER_AGENT)
                .build()
                .context("client error")?
                .post(format!("{url}/api/"))
                .form(&[
                    ("content", content),
                    ("lexer", "_text"),
                    ("format", "url"),
                    ("expires", "3600"),
                ])
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            Ok(text)
        }
    }

    #[async_trait]
    impl Command for Display {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let text = match parameter.get(&Rule::paste) {
                Some(&"dpaste") => {
                    Self::dpaste(
                        "https://dpaste.org",
                        *parameter.get(&Rule::content).unwrap(),
                    )
                    .await?
                }
                // no unicode support?
                Some(&"mozilla") | None => {
                    Self::dpaste(
                        "https://paste.mozilla.org",
                        *parameter.get(&Rule::content).unwrap(),
                    )
                    .await?
                }
                _ => return Err(Error::Message("do you REALLY need this pastebin?".into())),
            };

            let url = text.trim();

            // Collector
            if context.target().is_empty() {
                context.send_fmt(url).await
            } else {
                context
                    .send_fmt([
                        "[".into(),
                        MessageItem::url(format!(" {url} ").into()),
                        "]".into(),
                    ])
                    .await
            }
        }
    }
}
