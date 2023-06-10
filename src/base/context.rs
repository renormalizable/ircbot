use anyhow::Context as _;
use async_trait::async_trait;
use futures::prelude::*;
use tokio::sync::mpsc::*;
use tokio_stream::wrappers::UnboundedReceiverStream;

use super::{Error, Message};

// message context
#[async_trait]
pub trait Context: Sync {
    // bot name
    fn identity(&self) -> &str;
    // logical receiver
    fn receiver(&self) -> Option<&str>;
    // message sender
    fn source(&self) -> &str;
    // message receiver
    fn target(&self) -> &str;

    // send message
    async fn send_format(&self, target: &str, message: Message<'_>) -> Result<(), Error>;
    // send message stream
    async fn send_stream<'a>(
        &self,
        target: &str,
        stream: stream::BoxStream<'a, Message<'a>>,
    ) -> Result<(), Error> {
        stream
            .map(Ok)
            .try_for_each(|msg| self.send_format(target, msg))
            .await
    }

    async fn send_fmt<'a>(&self, message: impl Into<Message<'a>> + Send) -> Result<(), Error>
    where
        Self: Sized,
    {
        self.send_format(self.target(), message.into()).await
    }
    async fn send_itr<'a>(
        &self,
        iterator: impl Iterator<Item = impl Into<Message<'a>>> + Send,
    ) -> Result<(), Error>
    where
        Self: Sized,
    {
        self.send_stream(
            self.target(),
            stream::iter(iterator.map(|item| item.into())).boxed(),
        )
        .await
    }
    async fn send_stm<'a>(
        &self,
        stream: impl Stream<Item = impl Into<Message<'a>>> + Send,
    ) -> Result<(), Error>
    where
        Self: Sized,
    {
        self.send_stream(self.target(), stream.map(|item| item.into()).boxed())
            .await
    }
}

#[async_trait]
impl<T> Context for &T
where
    T: Context + ?Sized,
{
    fn identity(&self) -> &str {
        (**self).identity()
    }
    fn receiver(&self) -> Option<&str> {
        (**self).receiver()
    }
    fn source(&self) -> &str {
        (**self).source()
    }
    fn target(&self) -> &str {
        (**self).target()
    }

    async fn send_format(&self, target: &str, message: Message<'_>) -> Result<(), Error> {
        let future = (**self).send_format(target, message);

        future.await
    }
    async fn send_stream<'a>(
        &self,
        target: &str,
        stream: stream::BoxStream<'a, Message<'a>>,
    ) -> Result<(), Error> {
        let future = (**self).send_stream(target, stream);

        future.await
    }
}

#[async_trait]
impl<T> Context for Box<T>
where
    T: Context + ?Sized,
{
    fn identity(&self) -> &str {
        (**self).identity()
    }
    fn receiver(&self) -> Option<&str> {
        (**self).receiver()
    }
    fn source(&self) -> &str {
        (**self).source()
    }
    fn target(&self) -> &str {
        (**self).target()
    }

    async fn send_format(&self, target: &str, message: Message<'_>) -> Result<(), Error> {
        let future = (**self).send_format(target, message);

        future.await
    }
    async fn send_stream<'a>(
        &self,
        target: &str,
        stream: stream::BoxStream<'a, Message<'a>>,
    ) -> Result<(), Error> {
        let future = (**self).send_stream(target, stream);

        future.await
    }
}

// similar to BoxFuture and LocalBoxFuture
#[allow(dead_code)]
pub type BoxContext<'a> = Box<dyn Context + Send + 'a>;
#[allow(dead_code)]
pub type LocalBoxContext<'a> = Box<dyn Context + 'a>;

// collect output
pub struct Collector {
    sender: UnboundedSender<String>,
}

impl Collector {
    pub fn new() -> (Self, UnboundedReceiverStream<String>) {
        let (sender, receiver) = unbounded_channel();
        (Self { sender }, UnboundedReceiverStream::new(receiver))
    }
}

#[async_trait]
impl Context for Collector {
    fn identity(&self) -> &str {
        ""
    }
    fn receiver(&self) -> Option<&str> {
        None
    }
    fn source(&self) -> &str {
        ""
    }
    fn target(&self) -> &str {
        ""
    }

    async fn send_format(&self, _target: &str, message: Message<'_>) -> Result<(), Error> {
        self.sender
            .send(match message {
                Message::Text(text)
                | Message::Audio(_, text, _)
                | Message::Image(_, text)
                | Message::Video(_, text) => text.text(),
            })
            .context("Collector send error")?;

        Ok(())
    }
}
