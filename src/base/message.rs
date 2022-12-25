use mime::Mime;
use std::{borrow::Cow, time::Duration};

// modeled after MSC1767
// see [](https://github.com/matrix-org/matrix-spec-proposals/pull/1767)
pub enum Message<'a> {
    Audio(MessageData<'a>, Option<Duration>),
    Image(MessageData<'a>),
    Text(Vec<MessageText<'a>>),
    Video(MessageData<'a>),
}

#[derive(Default)]
pub struct MessageText<'a> {
    pub color: (Option<Color>, Option<Color>),
    pub style: Option<Vec<Style>>,
    pub text: Cow<'a, str>,
}

pub struct MessageData<'a> {
    pub link: Option<Cow<'a, str>>,
    pub text: Option<Cow<'a, str>>,
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

impl<'a> MessageText<'a> {
    pub fn url(text: Cow<'a, str>) -> Self {
        Self {
            color: (Some(Color::Navy), None),
            text,
            ..Default::default()
        }
    }
}

impl<'a> From<String> for MessageText<'a> {
    fn from(text: String) -> Self {
        Self {
            text: Cow::Owned(text),
            ..Default::default()
        }
    }
}

impl<'a> From<&'a str> for MessageText<'a> {
    fn from(text: &'a str) -> Self {
        Self {
            text: Cow::Borrowed(text),
            ..Default::default()
        }
    }
}

impl<'a> From<Cow<'a, str>> for MessageText<'a> {
    fn from(text: Cow<'a, str>) -> Self {
        Self {
            text,
            ..Default::default()
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
        Self::Text(vec![message])
    }
}

impl<'a> From<Vec<MessageText<'a>>> for Message<'a> {
    fn from(message: Vec<MessageText<'a>>) -> Self {
        Self::Text(message)
    }
}

impl<'a, const N: usize> From<[MessageText<'a>; N]> for Message<'a> {
    fn from(message: [MessageText<'a>; N]) -> Self {
        Self::Text(message.into_iter().collect())
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
