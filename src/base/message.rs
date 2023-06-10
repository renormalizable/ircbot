use mime::Mime;
use std::{borrow::Cow, time::Duration};

// modeled after MSC1767
// see [](https://github.com/matrix-org/matrix-spec-proposals/pull/1767)
pub enum Message<'a> {
    Audio(MessageData<'a>, MessageText<'a>, Option<Duration>),
    Image(MessageData<'a>, MessageText<'a>),
    Text(MessageText<'a>),
    Video(MessageData<'a>, MessageText<'a>),
}

#[derive(Default)]
pub struct MessageItem<'a> {
    pub color: (Option<Color>, Option<Color>),
    pub style: Option<Vec<Style>>,
    pub text: Cow<'a, str>,
}

#[derive(Default)]
pub struct MessageText<'a> {
    pub items: Vec<MessageItem<'a>>,
}

// see [](https://github.com/matrix-org/matrix-spec-proposals/pull/3551)
pub struct MessageData<'a> {
    pub link: Option<Cow<'a, str>>,
    pub name: Cow<'a, str>,
    pub mime: Mime,
    pub data: Vec<u8>,
}

pub enum Color {
    // css color 3
    // see [](https://www.w3.org/TR/css-color-3/)
    Black,
    Silver,
    Gray,
    White,
    Maroon,
    Red,
    Purple,
    Fuchsia,
    Green,
    Lime,
    Olive,
    Yellow,
    Navy,
    Blue,
    Teal,
    Aqua,
    // css color 4
    // see [](https://www.w3.org/TR/css-color-4/)
    LightGray,
    Orange,
    // rgba
    Rgba(u32),
}

pub enum Style {
    Bold,
    Italics,
    Underline,
    Spoiler,
}

impl<'a> MessageItem<'a> {
    pub fn url(text: Cow<'a, str>) -> Self {
        Self {
            color: (Some(Color::Navy), None),
            text,
            ..Default::default()
        }
    }
}

impl<'a> MessageText<'a> {
    pub fn text(&self) -> String {
        self.items.iter().map(|m| m.text.as_ref()).collect::<String>()
    }
}

impl<'a> From<String> for MessageItem<'a> {
    fn from(text: String) -> Self {
        Self {
            text: Cow::Owned(text),
            ..Default::default()
        }
    }
}

impl<'a> From<&'a str> for MessageItem<'a> {
    fn from(text: &'a str) -> Self {
        Self {
            text: Cow::Borrowed(text),
            ..Default::default()
        }
    }
}

impl<'a> From<Cow<'a, str>> for MessageItem<'a> {
    fn from(text: Cow<'a, str>) -> Self {
        Self {
            text,
            ..Default::default()
        }
    }
}

impl<'a> From<MessageItem<'a>> for MessageText<'a> {
    fn from(message: MessageItem<'a>) -> Self {
        Self {
            items: vec![message],
        }
    }
}

impl<'a> From<Vec<MessageItem<'a>>> for MessageText<'a> {
    fn from(message: Vec<MessageItem<'a>>) -> Self {
        Self { items: message }
    }
}

impl<'a, const N: usize> From<[MessageItem<'a>; N]> for MessageText<'a> {
    fn from(message: [MessageItem<'a>; N]) -> Self {
        Self {
            items: message.into_iter().collect(),
        }
    }
}

//impl<'a> From<Vec<u8>> for MessageData<'a> {
//    fn from(data: Vec<u8>) -> Self {
//        Self {
//            data,
//            ..Default::default()
//        }
//    }
//}

impl<'a> From<MessageText<'a>> for Message<'a> {
    fn from(message: MessageText<'a>) -> Self {
        Self::Text(message)
    }
}

// extra

impl<'a> From<String> for MessageText<'a> {
    fn from(text: String) -> Self {
        MessageItem::from(text).into()
    }
}

impl<'a> From<&'a str> for MessageText<'a> {
    fn from(text: &'a str) -> Self {
        MessageItem::from(text).into()
    }
}

impl<'a> From<Cow<'a, str>> for MessageText<'a> {
    fn from(text: Cow<'a, str>) -> Self {
        MessageItem::from(text).into()
    }
}

impl<'a> From<String> for Message<'a> {
    fn from(text: String) -> Self {
        MessageText::from(text).into()
    }
}

impl<'a> From<&'a str> for Message<'a> {
    fn from(text: &'a str) -> Self {
        MessageText::from(text).into()
    }
}

impl<'a> From<Cow<'a, str>> for Message<'a> {
    fn from(text: Cow<'a, str>) -> Self {
        MessageText::from(text).into()
    }
}

impl<'a> From<MessageItem<'a>> for Message<'a> {
    fn from(message: MessageItem<'a>) -> Self {
        MessageText::from(message).into()
    }
}

impl<'a> From<Vec<MessageItem<'a>>> for Message<'a> {
    fn from(message: Vec<MessageItem<'a>>) -> Self {
        MessageText::from(message).into()
    }
}

impl<'a, const N: usize> From<[MessageItem<'a>; N]> for Message<'a> {
    fn from(message: [MessageItem<'a>; N]) -> Self {
        MessageText::from(message).into()
    }
}
