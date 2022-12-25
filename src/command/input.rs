use anyhow::Context as _;
use async_trait::async_trait;
use futures::prelude::*;
use pest::Parser;
use pest_derive::Parser;
use serde::Deserialize;
use serde_json::value::RawValue;
use std::borrow::Cow;
use tracing::*;
use wana_kana::{to_hiragana, to_romaji};

use super::*;

pub use bim::Bim;
pub use gim::Gim;
pub use kana::Kana;
pub use romaji::Romaji;

mod kana {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
        input = _{ ^"kana" ~ WHITE_SPACE+ ~ romaji }
        romaji = { ANY+ }
    "#]
    pub struct Kana;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Kana {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            context
                .send_fmt(to_hiragana::to_hiragana(
                    parameter.get(&Rule::romaji).unwrap(),
                ))
                .await
        }
    }
}

mod romaji {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
        input = _{ ^"romaji" ~ WHITE_SPACE+ ~ kana }
        kana = { ANY+ }
    "#]
    pub struct Romaji;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Romaji {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            context
                .send_fmt(to_romaji::to_romaji(parameter.get(&Rule::kana).unwrap()))
                .await
        }
    }
}

#[async_trait]
trait InputMethod {
    async fn request<'a>(&self, input: Cow<'a, str>) -> Result<(String, Cow<'a, str>), Error>;

    async fn process(&self, input: Cow<'_, str>) -> Result<String, Error> {
        futures::stream::try_unfold(input, |input| async move {
            if input.is_empty() {
                Ok(None)
            } else {
                Ok(Some(self.request(input).await?))
            }
        })
        .try_collect::<String>()
        .await
    }
}

pub enum Element<'a> {
    String(Cow<'a, str>),
    Script(Cow<'a, str>),
}

macro_rules! split {
    ($type:ty) => {
        pub fn split<'a>(text: &'a str) -> Result<Vec<Element<'a>>, Error> {
            let vec = <$type>::parse(Rule::input, &text)
                .context("parse error")?
                .map(|pair| match pair.as_rule() {
                    Rule::text | Rule::comment => Element::String(pair.as_str().into()),
                    Rule::script => Element::Script(pair.as_str().into()),
                    _ => unreachable!(),
                })
                .collect::<Vec<_>>();

            Ok(vec)
        }
    };
}

mod pinyin {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
            input = _{ text? ~ ((delimiter ~ comment ~ delimiter | script) ~ text?)* }
            text = { (!character ~ ANY)+ }
            script = { character+ }
            comment = { (!delimiter ~ ANY)+ }
            character = _{ ASCII_ALPHA_LOWER | "'" }
            delimiter = _{ "''" }
        "#]
    struct Input;

    split!(Input);
}

mod shuangpin {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
            input = _{ text? ~ ((delimiter ~ comment ~ delimiter | script) ~ text?)* }
            text = { (!character ~ ANY)+ }
            script = { character+ }
            comment = { (!delimiter ~ ANY)+ }
            character = _{ ASCII_ALPHA_LOWER | ";" }
            delimiter = _{ "''" }
        "#]
    struct Input;

    split!(Input);
}

mod zhuyin {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
            input = _{ text? ~ ((delimiter ~ comment ~ delimiter | script) ~ text?)* }
            text = { (!character ~ ANY)+ }
            script = { character+ }
            comment = { (!delimiter ~ ANY)+ }
            character = _{ ASCII_ALPHA_LOWER | ASCII_DIGIT | "'" | "-" | ";" | "," | "." | "/" | "=" }
            delimiter = _{ "''" }
        "#]
    struct Input;

    split!(Input);
}

mod ja {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
            input = _{ text? ~ ((delimiter ~ comment ~ delimiter | script) ~ text?)* }
            text = { (!character ~ ANY)+ }
            script = { character+ }
            comment = { (!delimiter ~ ANY)+ }
            character = _{ ASCII_ALPHA_LOWER | ASCII_DIGIT | "'" | "-" }
            delimiter = _{ "''" }
        "#]
    struct Input;

    pub fn split<'a>(text: &'a str) -> Result<Vec<Element<'a>>, Error> {
        let vec = Input::parse(Rule::input, &text)
            .context("parse error")?
            .map(|pair| match pair.as_rule() {
                Rule::text | Rule::comment => Element::String(pair.as_str().into()),
                Rule::script => Element::Script(to_hiragana::to_hiragana(pair.as_str()).into()),
                _ => unreachable!(),
            })
            .collect::<Vec<_>>();

        Ok(vec)
    }
}

// see [](https://www.google.com/inputtools/try/)
mod gim {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
        input = _{ ^"gim" ~ (":" ~ lang)? ~ WHITE_SPACE+ ~ text }
        lang = { (!WHITE_SPACE ~ ANY)+ }
        text = { ANY+ }
    "#]
    pub struct Gim;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Gim {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let language = *parameter.get(&Rule::lang).unwrap_or(&"pinyins");
            let text = *parameter.get(&Rule::text).unwrap();

            let (method, input) = match language {
                // pinyin
                "pinyins" | "pinyin" | "zhs" | "zh" => ("zh-t-i0-pinyin", pinyin::split(text)?),
                "pinyint" | "zht" => ("zh-hant-t-i0-pinyin", pinyin::split(text)?),
                // wubi
                "wubi" | "ggtt" => ("zh-t-i0-wubi-1986", pinyin::split(text)?),
                // shuangpin
                // ms or ziranma?
                "shuangpinabc" | "vtpc" => {
                    ("zh-t-i0-pinyin-x0-shuangpin-abc", shuangpin::split(text)?)
                }
                "shuangpinms" => ("zh-t-i0-pinyin-x0-shuangpin-ms", shuangpin::split(text)?),
                "shuangpinflypy" | "ulpb" => {
                    ("zh-t-i0-pinyin-x0-shuangpin-flypy", shuangpin::split(text)?)
                }
                "shuangpinjiajia" | "ihpl" => (
                    "zh-t-i0-pinyin-x0-shuangpin-jiajia",
                    shuangpin::split(text)?,
                ),
                "shuangpinziguang" | "igpy" => (
                    "zh-t-i0-pinyin-x0-shuangpin-ziguang",
                    shuangpin::split(text)?,
                ),
                "shuangpinziranma" => (
                    "zh-t-i0-pinyin-x0-shuangpin-ziranma",
                    shuangpin::split(text)?,
                ),
                // zhuyin
                "zhuyin" | "5j4up=" => ("zh-hant-t-i0-und", zhuyin::split(text)?),
                // cangjie
                "cangjie" | "oiargrmbc" => ("zh-hant-t-i0-cangjie-1982", pinyin::split(text)?),
                // yue
                "yue" | "yut" => ("yue-hant-t-i0-und", pinyin::split(text)?),
                // ja
                "ja" => ("ja-t-ja-hira-i0-und", ja::split(text)?),
                _ => {
                    return Err(Error::Message(
                        "do you REALLY need this input method?".into(),
                    ))
                }
            };
            let worker = Worker(method);

            context
                .send_fmt(
                    input
                        .into_iter()
                        .map(|ele| async {
                            match ele {
                                Element::String(s) => Ok(s),
                                Element::Script(s) => worker.process(s).await.map(|x| x.into()),
                            }
                        })
                        .collect::<stream::FuturesOrdered<_>>()
                        .try_collect::<String>()
                        .await?,
                )
                .await
        }
    }

    struct Worker<'a>(&'a str);

    #[async_trait]
    impl InputMethod for Worker<'_> {
        async fn request<'a>(&self, input: Cow<'a, str>) -> Result<(String, Cow<'a, str>), Error> {
            // NOTE input trancates rougly at 96
            let text = reqwest::Client::new()
                .post("https://inputtools.google.com/request")
                .form(&[
                    ("itc", self.0),
                    // number of candidates
                    // NOTE matched_length sometimes disappears if num = 1
                    ("num", "1"),
                    ("cp", "0"),
                    ("cs", "1"),
                    //("cs", "0"),
                    ("ie", "utf-8"),
                    ("oe", "utf-8"),
                    ("app", "demopage"),
                    //("app", "jsapi"),
                    ("text", &input),
                ])
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            let response =
                serde_json::from_str::<Response>(&text).context(format!("json error: {text}"))?;
            info!("{response:?}");

            let response = response.result.into_iter().next();

            match response {
                Some(ResponseResult {
                    input,
                    candidate,
                    // NOTE the matched_length returned from the api seems to be wrong
                    remainder: ResponseRemainder { matched_length, .. },
                    ..
                }) => Ok((
                    candidate.into_iter().next().unwrap_or("").into(),
                    match matched_length.as_deref() {
                        Some(&[length, ..]) => Cow::Owned(input[length..].to_owned()),
                        _ => "".into(),
                    },
                )),
                _ => Err(Error::NoOutput),
            }
        }
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Response<'a> {
        status: &'a str,
        #[serde(borrow)]
        result: Vec<ResponseResult<'a>>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct ResponseResult<'a> {
        input: &'a str,
        #[serde(borrow)]
        candidate: Vec<&'a str>,
        // NOTE this field seems to be empty
        #[serde(borrow)]
        empty: Vec<&'a str>,
        #[serde(borrow)]
        remainder: ResponseRemainder<'a>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct ResponseRemainder<'a> {
        #[serde(borrow)]
        annotation: Option<Vec<&'a str>>,
        candidate_type: Vec<u64>,
        #[serde(borrow)]
        lc: Option<Vec<&'a str>>,
        matched_length: Option<Vec<usize>>,
    }
}

mod bim {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
        input = _{ ^"bim" ~ WHITE_SPACE+ ~ text }
        text = { ANY+ }
    "#]
    pub struct Bim;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Bim {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let text = *parameter.get(&Rule::text).unwrap();

            let input = pinyin::split(text)?;
            let worker = Worker;

            context
                .send_fmt(
                    input
                        .into_iter()
                        .map(|ele| async {
                            match ele {
                                Element::String(s) => Ok(s),
                                Element::Script(s) => worker.process(s).await.map(|x| x.into()),
                            }
                        })
                        .collect::<stream::FuturesOrdered<_>>()
                        .try_collect::<String>()
                        .await?,
                )
                .await
        }
    }

    struct Worker;

    #[async_trait]
    impl InputMethod for Worker {
        async fn request<'a>(&self, input: Cow<'a, str>) -> Result<(String, Cow<'a, str>), Error> {
            // NOTE input cannot be too long ~430 or ~110
            let text = reqwest::Client::new()
                .get("https://olime.baidu.com/py")
                .query(&[
                    ("inputtype", "py"),
                    ("bg", "0"),
                    ("ed", "5"),
                    ("result", "hanzi"),
                    ("resultcoding", "unicode"),
                    ("ch_en", "0"),
                    ("clientinfo", "web"),
                    ("version", "1"),
                    ("input", &input),
                ])
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            let response =
                serde_json::from_str::<Response>(&text).context(format!("json error: {text}"))?;
            info!("{response:?}");

            let result = response.result.0.into_iter().next();

            match result {
                Some((res, len, _)) if len != 0 => Ok((
                    res.into(),
                    // NOTE the api has changed
                    //match input {
                    //    Cow::Borrowed(s) => Cow::Borrowed(&s[len..]),
                    //    Cow::Owned(mut s) => Cow::Owned(s.split_off(len)),
                    //},
                    "".into(),
                )),
                _ => Err(Error::NoOutput),
            }
        }
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Response<'a> {
        status: &'a str,
        errmsg: &'a str,
        errno: &'a str,
        #[serde(borrow)]
        result: (Vec<(&'a str, usize, &'a RawValue)>, &'a str),
    }
}
