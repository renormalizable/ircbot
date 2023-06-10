use async_trait::async_trait;
use futures::{stream, StreamExt, TryStreamExt};
use irc::client::{prelude::ChannelExt, Sender};
use pest::Parser;
use pest_derive::Parser;
use regex::Regex;
use std::{borrow::Cow, convert::identity, fmt};
use tracing::*;

use super::{normalize, LineBreaker};
use crate::{
    base::{self, Color, Error, Message, MessageData, MessageItem, Style},
    command::scheme::Display,
};

#[derive(Parser)]
#[grammar = "client/irc.pest"]
struct MessageParser;

pub struct MessageContext {
    identity: String,
    receiver: Option<String>,
    source: String,
    target: String,
    message: String,
    sender: Sender,
}

impl fmt::Debug for MessageContext {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(
            f,
            "[{} => {}] <{}> {:?}: {:?}",
            self.identity, self.target, self.source, self.receiver, self.message
        )
    }
}

impl MessageContext {
    pub fn new(
        identity: String,
        source: String,
        target: String,
        message: String,
        sender: Sender,
    ) -> Self {
        let escape =
            Regex::new(r"\x02|\x04|\x06|\x07|\x0f|\x16|\x1b|\x1d|\x1f|\x03(\d{1,2}(,\d{1,2})?)?")
                .unwrap();

        let mut src = None;
        let mut tgt = None;
        let mut msg = None;

        match MessageParser::parse(Rule::input, &message) {
            Ok(rules) => {
                for part in rules {
                    let val = escape.replace_all(part.as_str(), "");
                    match part.as_rule() {
                        Rule::source => src = Some(val.into_owned()),
                        Rule::target => tgt = Some(val.into_owned()),
                        Rule::message => msg = Some(val.trim_end().to_owned()),
                        _ => (),
                    }
                }
            }
            Err(error) => warn!("parse error: {:?}", error),
        };

        let source = src.unwrap_or(source);

        if target.is_channel_name() {
            // channel
            let target = target;

            Self {
                identity,
                receiver: tgt.or(Some(source.clone())),
                source,
                target,
                message: msg.unwrap_or(message),
                sender,
            }
        } else {
            // direct message
            let target = tgt.unwrap_or(source.clone());

            Self {
                identity,
                receiver: None,
                source,
                target,
                message: msg.unwrap_or(message),
                sender,
            }
        }
    }

    pub fn message(&self) -> &str {
        &self.message
    }

    async fn send(&self, target: &str, message: &str) -> Result<(), Error> {
        self.sender
            .send_privmsg(target, message)
            .map_err(|_| Error::SendError)
    }

    async fn paste(text: &str) -> Result<String, Error> {
        let len = text.len() >> 10;
        let text = Display::dpaste("https://paste.mozilla.org", text).await?;
        let url = text.trim();

        Ok(format!("tl;dr [\x0302 {url} \x0f] {len}KB"))
    }
}

#[async_trait]
impl base::Context for MessageContext {
    fn identity(&self) -> &str {
        &self.source
    }
    fn receiver(&self) -> Option<&str> {
        self.receiver.as_deref()
    }
    fn source(&self) -> &str {
        &self.source
    }
    fn target(&self) -> &str {
        &self.target
    }

    async fn send_format(&self, target: &str, message: Message<'_>) -> Result<(), Error> {
        let message = match message {
            Message::Text(text) => text.items,
            #[allow(unused_variables)]
            Message::Audio(
                MessageData {
                    link: Some(url),
                    name,
                    mime,
                    data,
                },
                text,
                _,
            )
            | Message::Image(
                MessageData {
                    link: Some(url),
                    name,
                    mime,
                    data,
                },
                text,
            ) => {
                let mut vec = vec![
                    format!("{} [", mime.essence_str()).into(),
                    MessageItem::url(format!(" {url} ").into()),
                    "]".into(),
                ];

                if !text.items.is_empty() {
                    vec.push(" ".into());
                    vec.extend(text.items);
                }

                vec
            }
            _ => return Ok(()),
        };

        let message = message
            .into_iter()
            .map(|MessageItem { color, style, text }| {
                use Style::*;

                let text = match (
                    color.0.and_then(translate_color),
                    color.1.and_then(translate_color),
                ) {
                    (Some(color0), None) => format_color(text, &color0),
                    (None, Some(color1)) => format_color(text, &format!(",{color1}")),
                    (Some(color0), Some(color1)) => {
                        format_color(text, &format!("{color0},{color1}"))
                    }
                    _ => text,
                };

                let text = match style {
                    Some(styles) => styles.iter().fold(text, |text, style| match style {
                        Bold => Cow::Owned(format!("\x02{text}\x0f")),
                        Italics => Cow::Owned(format!("\x1d{text}\x0f")),
                        Underline => Cow::Owned(format!("\x1f{text}\x0f")),
                        Spoiler => Cow::Owned(format!("\x0301,01{text}\x0f")),
                    }),
                    _ => text,
                };

                text
            })
            .collect::<String>();
        let message = normalize(&message).join("\x0304\\n\x0f ");

        if message.len() > 0x400 {
            self.send(target, &Self::paste(&message).await?).await
        } else {
            futures::stream::iter(LineBreaker::new(
                // (512 - 2) / 3 = 170
                // 420 bytes should be safe
                420,
                &match self.receiver() {
                    Some(receiver) => format!("{receiver}: {message}"),
                    None => message,
                },
            ))
            .map(Ok)
            .try_for_each(|msg| async move {
                match self.send(target, msg).await {
                    Ok(_) => Ok(()),
                    Err(err) => Err(Err(err)),
                }
            })
            .await
            .map_or_else(identity, |_| Ok(()))
        }
    }

    async fn send_stream<'a>(
        &self,
        target: &str,
        stream: stream::BoxStream<'a, Message<'a>>,
    ) -> Result<(), Error> {
        let result = stream
            .map(Ok)
            .try_fold(0, |ind, msg| async move {
                if ind < 15 {
                    match self.send_format(target, msg).await {
                        Ok(_) => Ok(ind + 1),
                        Err(err) => Err(Err(err)),
                    }
                } else {
                    Err(match self.receiver() {
                        Some(receiver) => {
                            self.send_format(target, format!("{receiver}: 太长了啦...").into())
                                .await
                        }
                        None => self.send_format(target, "太长了啦...".into()).await,
                    })
                }
            })
            .await;

        match result {
            Ok(0) => Err(Error::NoOutput),
            Ok(_) => Ok(()),
            Err(result) => result,
        }
    }
}

fn translate_color(color: Color) -> Option<Cow<'static, str>> {
    use Color::*;

    match color {
        Black => Some("01".into()),
        Silver => None,
        Gray => Some("14".into()),
        White => Some("00".into()),
        Maroon => Some("05".into()),
        Red => Some("04".into()),
        Purple => Some("06".into()),
        Fuchsia => Some("13".into()),
        Green => Some("03".into()),
        Lime => Some("09".into()),
        Olive => None,
        Yellow => Some("08".into()),
        Navy => Some("02".into()),
        Blue => Some("12".into()),
        Teal => Some("10".into()),
        Aqua => Some("11".into()),
        LightGray => Some("15".into()),
        Orange => Some("07".into()),
        _ => None,
    }
}

fn format_color<'a>(text: Cow<'_, str>, color: &str) -> Cow<'a, str> {
    Cow::Owned(format!("\x03{color}{text}\x0f"))
}
