use anyhow::Context as _;
use async_trait::async_trait;
use futures::{stream, StreamExt, TryFutureExt, TryStreamExt};
use matrix_sdk::{
    room::{Room, RoomMember},
    ruma::{
        events::{
            relation::{InReplyTo, Replacement},
            room::message::{
                AudioInfo, AudioMessageEventContent, ForwardThread, ImageMessageEventContent,
                MessageType, OriginalRoomMessageEvent, Relation, RoomMessageEventContent,
            },
            room::ImageInfo,
            AnyMessageLikeEvent, AnyMessageLikeEventContent, MessageLikeEvent,
        },
        RoomId,
    },
    Client,
};
use pest::Parser;
use pest_derive::Parser;
use std::borrow::Cow;
use tracing::*;

use super::normalize;
use crate::{
    base::{self, Color, Error, Message, MessageItem, Style},
    command::scheme::Display,
};

#[derive(Parser)]
#[grammar = "client/matrix.pest"]
struct MessageParser;

// NOTE the reply format is determined as follows
//     1. if there is no reply or mention -> format as reply to the event
//     2. if the event is a reply -> format as reply to the original event
//     3. if the event is a mention -> format as mention
pub struct MessageContext {
    event: OriginalRoomMessageEvent,
    reply: Option<AnyMessageLikeEvent>,
    receiver: Option<RoomMember>,
    message: String,
    // send
    room: Room,
    // upload
    client: Client,
}

impl MessageContext {
    pub fn new(
        event: OriginalRoomMessageEvent,
        reply: Option<AnyMessageLikeEvent>,
        members: Vec<RoomMember>,
        room: Room,
        client: Client,
    ) -> Vec<Self> {
        let content = match &event.content.relates_to {
            Some(Relation::Replacement(Replacement { new_content, .. })) => {
                new_content.msgtype.body()
            }
            _ => event.content.body(),
        };
        match MessageParser::parse(Rule::input, content) {
            Ok(rules) => rules
                .filter_map(|line| {
                    let message = line.into_inner();

                    let mut src = None;
                    let mut tgt = None;
                    let mut msg = None;

                    for part in message {
                        let val = part.as_str();
                        match part.as_rule() {
                            Rule::source => src = Some(val.to_owned()),
                            Rule::target => tgt = Some(val.to_owned()),
                            Rule::message => msg = Some(val.trim_end().to_owned()),
                            _ => (),
                        }
                    }

                    msg.map(|message| Self {
                        event: event.clone(),
                        reply: reply.clone(),
                        receiver: tgt.or(src).and_then(|name| {
                            members
                                .iter()
                                .filter_map(|member| match member.display_name() {
                                    Some(_name) if _name == name => Some(member.to_owned()),
                                    _ => None,
                                })
                                .next()
                        }),
                        message,
                        room: room.clone(),
                        client: client.clone(),
                    })
                })
                .collect(),
            Err(error) => {
                warn!("parse error: {:?}", error);
                Vec::new()
            }
        }
    }

    pub fn message(&self) -> &str {
        &self.message
    }

    pub fn room(&self) -> &Room {
        &self.room
    }

    fn get_room(&self, target: &str) -> Option<Room> {
        use base::Context;

        if target == self.target() {
            Some(self.room.clone())
        } else {
            <&RoomId>::try_from(target)
                .ok()
                .and_then(|room_id| self.client.get_room(room_id))
        }
    }
    // NOTE matrix-appservice-irc uses text for reply while uses html for normal message
    fn set_reply_to(&self, mut content: RoomMessageEventContent) -> RoomMessageEventContent {
        match &self.reply {
            None => {
                content.msgtype = match content.msgtype {
                    MessageType::Text(mut text) => {
                        // NOTE matrix-appservice-irc needs a newline to bridge the reply properly
                        text.body = format!("\n{}", text.body);
                        MessageType::Text(text)
                    }
                    _ => content.msgtype,
                };
                content.make_reply_to(&self.event, ForwardThread::Yes)
            }
            Some(AnyMessageLikeEvent::RoomMessage(MessageLikeEvent::Original(event))) => {
                content.msgtype = match content.msgtype {
                    MessageType::Text(mut text) => {
                        // NOTE matrix-appservice-irc needs a newline to bridge the reply properly
                        text.body = format!("\n{}", text.body);
                        MessageType::Text(text)
                    }
                    _ => content.msgtype,
                };
                match &self.event.content.relates_to {
                    // NOTE replacement can only be applied to an original event
                    Some(Relation::Replacement(Replacement { new_content, .. })) => {
                        let mut new_event = event.clone();
                        new_event.content.msgtype = new_content.msgtype.clone();
                        content.make_reply_to(&new_event, ForwardThread::Yes)
                    }
                    _ => content.make_reply_to(event, ForwardThread::Yes),
                }
            }
            Some(event) => {
                content.relates_to = Some(Relation::Reply {
                    in_reply_to: InReplyTo::new(event.event_id().to_owned()),
                });
                content
            }
        }
    }

    async fn paste(text: &str) -> Result<(String, String), Error> {
        let len = text.len() >> 10;
        let text = Display::dpaste("https://paste.mozilla.org", text).await?;
        let url = text.trim();

        Ok((
            format!(r#"tl;dr [ {url} ] {len}KB"#),
            format!(r#"tl;dr [<font color="navy"> {url} </font>] {len}KB"#),
        ))
    }
    async fn send(room: &Room, content: RoomMessageEventContent) -> Result<(), Error> {
        let event = AnyMessageLikeEventContent::RoomMessage(content);

        room.send(event, None)
            .await
            .map(|_| ())
            .map_err(|_| Error::SendError)
    }
}

#[async_trait]
impl base::Context for MessageContext {
    fn identity(&self) -> &str {
        self.room.own_user_id().as_str()
    }
    fn receiver(&self) -> Option<&str> {
        // prefer reply over mention
        self.reply
            .as_ref()
            .map(|event| event.sender().as_str())
            .or(self
                .receiver
                .as_ref()
                .map(|member| member.user_id().as_str()))
            .or(Some(self.event.sender.as_str()))
    }
    fn source(&self) -> &str {
        // only use event as source
        self.event.sender.as_str()
    }
    fn target(&self) -> &str {
        self.event.room_id.as_str()
    }

    async fn send_format(&self, target: &str, message: Message<'_>) -> Result<(), Error> {
        let room = self.get_room(target).ok_or(Error::SendError)?;

        let _ = room.typing_notice(true).await;

        let result = match message {
            Message::Text(message) => {
                let text = message.text();

                let html = message
                    .items
                    .into_iter()
                    .map(|MessageItem { color, style, text }| {
                        use Style::*;

                        let text = match color.0.and_then(translate_color) {
                            Some(color) => format_color(text, &color),
                            _ => text,
                        };

                        let text = match style {
                            Some(styles) => styles.iter().fold(text, |text, style| match style {
                                Bold => Cow::Owned(format!("<b>{text}</b>")),
                                Italics => Cow::Owned(format!("<i>{text}</i>")),
                                Underline => Cow::Owned(format!("<u>{text}</u>")),
                                Spoiler => {
                                    Cow::Owned(format!("<span data-mx-spoiler>{text}</span>"))
                                }
                            }),
                            _ => text,
                        };

                        text
                    })
                    .collect::<String>();

                let text = normalize(&text).join("\n");
                //let text = normalize(&html).join("\n");
                let html = normalize(&html).join("<br>");

                // NOTE matrix event has a size limit of 64kb or 0x10000
                let (text, html) = if text.len() + html.len() > 0xf000 {
                    Self::paste(&text).await?
                } else {
                    (text, html)
                };

                let content = match (&self.receiver, &self.reply) {
                    (Some(member), None) => {
                        // NOTE matrix_to_uri escapes @ and : in link, which makes element-ios unhappy
                        let link = member.user_id().matrix_to_uri();
                        let name = member.display_name().unwrap_or(self.source());

                        RoomMessageEventContent::text_html(
                            format!("{name}: {text}"),
                            format!(r#"<a href="{link}">{name}</a>: {html}"#),
                        )
                    }
                    _ => self.set_reply_to(RoomMessageEventContent::text_html(text, html)),
                };

                Self::send(&room, content).await
            }
            Message::Image(message, text) => {
                let len = message.data.len();
                let uri = self
                    .client
                    .media()
                    .upload(&message.mime, message.data)
                    .await
                    .context("upload error")?
                    .content_uri;

                let content = RoomMessageEventContent::new(MessageType::Image(
                    ImageMessageEventContent::plain(normalize(&text.text()).join("\n"), uri).info(
                        {
                            let mut info = ImageInfo::new();
                            info.mimetype = Some(message.mime.essence_str().into());
                            info.size = Some(len.try_into().context("convert error")?);
                            Box::new(info)
                        },
                    ),
                ));
                let content = match (&self.receiver, &self.reply) {
                    (Some(_), None) => content,
                    _ => self.set_reply_to(content),
                };

                Self::send(&room, content).await
            }
            Message::Audio(message, text, duration) => {
                let len = message.data.len();
                let uri = self
                    .client
                    .media()
                    .upload(&message.mime, message.data)
                    .await
                    .context("upload error")?
                    .content_uri;

                let content = RoomMessageEventContent::new(MessageType::Audio(
                    AudioMessageEventContent::plain(normalize(&text.text()).join("\n"), uri).info(
                        {
                            let mut info = AudioInfo::new();
                            info.duration = duration;
                            // make mautrix happy
                            info.mimetype = Some(message.mime.essence_str().into());
                            info.size = Some(len.try_into().context("convert error")?);
                            Box::new(info)
                        },
                    ),
                ));
                let content = match (&self.receiver, &self.reply) {
                    (Some(_), None) => content,
                    _ => self.set_reply_to(content),
                };

                Self::send(&room, content).await
            }
            _ => Ok(()),
        };

        // NOTE sometimes this doesn't clear the notice
        let _ = room.typing_notice(false).await;

        result
    }
    async fn send_stream<'a>(
        &self,
        target: &str,
        stream: stream::BoxStream<'a, Message<'a>>,
    ) -> Result<(), Error> {
        // merge text messages into a single message
        stream
            .map(Ok)
            .try_fold((0, Vec::new()), |(ind, mut buffer), message| async move {
                match message {
                    Message::Text(text) => {
                        buffer.extend(text.items.into_iter());
                        buffer.push("\n".into());
                        Ok((ind + 1, buffer))
                    }
                    _ => {
                        buffer.pop();
                        if !buffer.is_empty() {
                            self.send_format(target, Message::Text(buffer.into()))
                                .await?;
                        }

                        self.send_format(target, message)
                            .await
                            .map(|_| (ind + 1, Vec::new()))
                    }
                }
            })
            .and_then(|(ind, mut buffer)| async move {
                // empty stream
                if ind == 0 {
                    Err(Error::NoOutput)
                } else {
                    buffer.pop();
                    if !buffer.is_empty() {
                        self.send_format(target, Message::Text(buffer.into()))
                            .await?;
                    }

                    Ok(())
                }
            })
            .await
    }

    async fn send_direct(&self, target: &str, message: Message<'_>) -> Result<(), Error> {
        let room = self.get_room(target).ok_or(Error::SendError)?;

        let _ = room.typing_notice(true).await;

        let message = match message {
            Message::Text(text)
            | Message::Audio(_, text, _)
            | Message::Image(_, text)
            | Message::Video(_, text) => text.text(),
        };

        let result = Self::send(&room, RoomMessageEventContent::text_plain(message)).await;

        // NOTE sometimes this doesn't clear the notice
        let _ = room.typing_notice(false).await;

        result
    }
}

fn translate_color(color: Color) -> Option<Cow<'static, str>> {
    use Color::*;

    match color {
        Black => Some("black".into()),
        Silver => Some("silver".into()),
        Gray => Some("gray".into()),
        White => Some("white".into()),
        Maroon => Some("maroon".into()),
        Red => Some("red".into()),
        Purple => Some("purple".into()),
        Fuchsia => Some("fuchsia".into()),
        Green => Some("green".into()),
        Lime => Some("lime".into()),
        Olive => Some("olive".into()),
        Yellow => Some("yellow".into()),
        Navy => Some("navy".into()),
        Blue => Some("blue".into()),
        Teal => Some("teal".into()),
        Aqua => Some("aqua".into()),
        LightGray => Some("lightgray".into()),
        Orange => Some("orange".into()),
        Rgba(rgba) => Some(format!("#{:X}", rgba >> 8).into()),
    }
}

fn format_color<'a>(text: Cow<'_, str>, color: &str) -> Cow<'a, str> {
    Cow::Owned(format!(r#"<font color="{color}">{text}</font>"#))
}
