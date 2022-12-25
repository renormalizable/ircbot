use anyhow::Context as _;
use async_trait::async_trait;
use fuzzy_matcher::{skim, FuzzyMatcher};
use pest_derive::Parser;
use rand::prelude::*;
use regex::{Captures, Regex};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::{borrow::Cow, collections::HashMap};
use tracing::*;

use super::*;

pub use bangumi::Bangumi;
pub use btran::{Btran, BtranConfig};
pub use crates_io::CratesIo;
pub use google::{Google, GoogleConfig};
pub use gtran::{Gtran, GtranConfig};
pub use ipapi::Ipapi;
pub use movie::Movie;
pub use poke::Poke;
pub use speedrun::Speedrun;
pub use urban::Urban;
pub use wolfram::{Wolfram, WolframConfig};

// see [](https://products.wolframalpha.com/api/documentation/)
mod wolfram {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r##"
        input = _{ ^"wolfram" ~ WHITE_SPACE+ ~ text ~ (WHITE_SPACE+ ~ pager)? }
        text = { (!(WHITE_SPACE+ ~ pager) ~ ANY)+ }
        pager = _{ "#" ~ length ~ ("+" ~ offset)? | "+" ~ offset }
        length = { ASCII_DIGIT+ }
        offset = { ASCII_DIGIT+ }
    "##]
    pub struct Wolfram {
        appid: String,
    }

    #[derive(Debug, Deserialize, Serialize)]
    pub struct WolframConfig {
        pub appid: String,
    }

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    impl Wolfram {
        pub fn new(config: &WolframConfig) -> Self {
            Self {
                appid: config.appid.to_owned(),
            }
        }
    }

    #[async_trait]
    impl Command for Wolfram {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let offset = parameter
                .get(&Rule::offset)
                .map(|x| x.parse().unwrap())
                .unwrap_or(0);
            let length = parameter
                .get(&Rule::length)
                .map(|x| x.parse().unwrap())
                .unwrap_or(2);

            let text = reqwest::Client::new()
                .get("https://api.wolframalpha.com/v2/query")
                .query(&[
                    ("format", "plaintext,image,wav"),
                    ("units", "metric"),
                    ("input", parameter.get(&Rule::text).unwrap()),
                    ("output", "json"),
                    ("appid", &self.appid),
                ])
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;
            ("{text:?}");

            let result = serde_json::from_str::<Response>(&text)
                .context(format!("json error: {text}"))?
                .query_result;

            if let Some(pods) = result.pods {
                let escape = Regex::new(r"\\:([0-9a-f]{4})").unwrap();

                let items = pods.into_iter().map(|pod| {
                    let subpods = pod.subpods.unwrap_or(Vec::new());

                    let text = subpods
                        .iter()
                        .filter_map(|subpod| {
                            subpod.plain_text.as_ref().map(|text| {
                                escape
                                    .replace_all(&text, |captures: &Captures| {
                                        let code = u32::from_str_radix(
                                            captures.get(0).unwrap().as_str(),
                                            16,
                                        )
                                        .unwrap();
                                        char::from_u32(code).unwrap().to_string()
                                    })
                                    .into_owned()
                            })
                        })
                        .collect::<Vec<_>>()
                        .join(" ");

                    let image = subpods
                        .into_iter()
                        .filter_map(|subpod| subpod.img)
                        .collect::<Vec<_>>()
                        .pop();

                    (pod.title, text, image)
                });

                let output = items.skip(offset).map(|item| {
                    [
                        MessageText {
                            style: Some(vec![Style::Bold]),
                            text: format!("{}:", item.0).into(),
                            ..Default::default()
                        },
                        " ".into(),
                        item.1.into(),
                    ]
                });

                return if length != 0 {
                    context.send_itr(output.take(length)).await
                } else {
                    context.send_itr(output).await
                };
            }

            if let Some(did_you_mean) =
                result
                    .did_you_means
                    .and_then(|did_you_means| match did_you_means {
                        DidYouMeans::Item(item) => Some(item),
                        DidYouMeans::List(list) => list.into_iter().next(),
                    })
            {
                return Err(Error::Message(format!(
                    "did you mean '{}'?",
                    did_you_mean.val
                )));
            }

            Err(Error::Message("no output".into()))
        }
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Response<'a> {
        #[serde(borrow)]
        #[serde(rename = "queryresult")]
        query_result: QueryResult<'a>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct QueryResult<'a> {
        success: bool,
        #[serde(borrow)]
        #[serde(rename = "inputstring")]
        input_string: Cow<'a, str>,
        timing: f32,
        timedout: &'a str,
        #[serde(borrow)]
        recalculate: Cow<'a, str>,
        version: &'a str,
        #[serde(rename = "numpods")]
        num_pods: u64,
        #[serde(borrow)]
        host: Cow<'a, str>,
        #[serde(rename = "datatypes")]
        data_types: &'a str,
        #[serde(rename = "parsetiming")]
        parse_timing: f32,
        server: &'a str,
        //#[serde(rename = "parseidserver")]
        //parse_id_server: &'a str,
        #[serde(rename = "timedoutpods")]
        timedout_pods: &'a str,
        id: &'a str,
        #[serde(rename = "parsetimedout")]
        parse_timedout: bool,
        #[serde(borrow)]
        related: Cow<'a, str>,
        #[serde(borrow)]
        pods: Option<Vec<Pod<'a>>>,
        //#[serde(borrow)]
        //assumptions: Option<Assumption<'a>>,
        //#[serde(borrow)]
        //#[serde(rename = "userinfoused")]
        //user_info_used: Option<UserInfoUsed<'a>>,
        //#[serde(borrow)]
        //sources: Option<Source<'a>>,
        #[serde(borrow)]
        #[serde(rename = "didyoumeans")]
        did_you_means: Option<DidYouMeans<'a>>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Pod<'a> {
        #[serde(borrow)]
        title: Cow<'a, str>,
        scanner: &'a str,
        id: &'a str,
        position: u64,
        #[serde(rename = "numsubpods")]
        num_subpods: u64,
        subpods: Option<Vec<Subpod<'a>>>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Subpod<'a> {
        #[serde(borrow)]
        title: Cow<'a, str>,
        #[serde(borrow)]
        img: Option<Image<'a>>,
        #[serde(borrow)]
        #[serde(rename = "plaintext")]
        plain_text: Option<Cow<'a, str>>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Image<'a> {
        #[serde(borrow)]
        src: Cow<'a, str>,
        #[serde(borrow)]
        alt: Cow<'a, str>,
        #[serde(borrow)]
        title: Cow<'a, str>,
        #[serde(borrow)]
        #[serde(rename = "contenttype")]
        content_type: Cow<'a, str>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Assumption<'a> {
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct UserInfoUsed<'a> {
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    #[serde(untagged)]
    enum DidYouMeans<'a> {
        #[serde(borrow)]
        Item(DidYouMean<'a>),
        #[serde(borrow)]
        List(Vec<DidYouMean<'a>>),
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct DidYouMean<'a> {
        #[serde(borrow)]
        val: Cow<'a, str>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }
}

// see [](https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list)
mod google {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r##"
        input = _{ ^"google" ~ WHITE_SPACE+ ~ text ~ (WHITE_SPACE+ ~ pager)? }
        text = { (!(WHITE_SPACE+ ~ pager) ~ ANY)+ }
        pager = _{ "#" ~ length ~ ("+" ~ offset)? | "+" ~ offset }
        length = { ASCII_DIGIT+ }
        offset = { ASCII_DIGIT+ }
    "##]
    pub struct Google {
        key: String,
        seid: String,
    }

    #[derive(Debug, Deserialize, Serialize)]
    pub struct GoogleConfig {
        pub key: String,
        pub seid: String,
    }

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    impl Google {
        pub fn new(config: &GoogleConfig) -> Self {
            Self {
                key: config.key.to_owned(),
                seid: config.seid.to_owned(),
            }
        }
    }

    #[async_trait]
    impl Command for Google {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let offset = parameter
                .get(&Rule::offset)
                .map(|x| x.parse().unwrap())
                .unwrap_or(0);
            let length = parameter
                .get(&Rule::length)
                .map(|x| x.parse().unwrap())
                .unwrap_or(1);

            let text = reqwest::Client::new()
                .get("https://customsearch.googleapis.com/customsearch/v1")
                .query(&[
                    ("q", parameter.get(&Rule::text).unwrap() as &str),
                    ("key", &self.key),
                    ("cx", &self.seid),
                ])
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            let response =
                serde_json::from_str::<Response>(&text).context(format!("json error: {text}"))?;

            let items = match response.items {
                Some(items) => items
                    .into_iter()
                    .filter(|x| !x.link.to_lowercase().contains("toutiao")),
                None => {
                    return Err(if let Some(spelling) = response.spelling {
                        Error::Message(format!("did you mean '{}'?", spelling.corrected_query))
                    } else {
                        Error::NoOutput
                    })
                }
            };

            let output = items.skip(offset).map(|item| {
                [
                    item.title.into(),
                    " [".into(),
                    MessageText::url(format!(" {} ", item.link).into()),
                    "] ".into(),
                    item.snippet.unwrap_or("".into()).into(),
                ]
            });

            if length != 0 {
                context.send_itr(output.take(length)).await
            } else {
                context.send_itr(output).await
            }
        }
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Response<'a> {
        #[serde(borrow)]
        items: Option<Vec<Item<'a>>>,
        #[serde(borrow)]
        spelling: Option<Spelling<'a>>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Item<'a> {
        #[serde(borrow)]
        title: Cow<'a, str>,
        #[serde(borrow)]
        #[serde(rename = "htmlTitle")]
        html_title: Cow<'a, str>,
        #[serde(borrow)]
        link: Cow<'a, str>,
        #[serde(borrow)]
        #[serde(rename = "displayLink")]
        display_link: Cow<'a, str>,
        #[serde(borrow)]
        snippet: Option<Cow<'a, str>>,
        #[serde(borrow)]
        #[serde(rename = "htmlSnippet")]
        html_snippet: Option<Cow<'a, str>>,
        #[serde(borrow)]
        #[serde(rename = "formattedUrl")]
        formatted_url: Cow<'a, str>,
        #[serde(borrow)]
        #[serde(rename = "htmlFormattedUrl")]
        html_formatted_url: Cow<'a, str>,
        #[serde(borrow)]
        #[serde(rename = "pagemap")]
        page_map: Option<PageMap<'a>>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct PageMap<'a> {
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Spelling<'a> {
        #[serde(borrow)]
        #[serde(rename = "correctedQuery")]
        corrected_query: Cow<'a, str>,
        #[serde(borrow)]
        #[serde(rename = "htmlCorrectedQuery")]
        html_corrected_query: Cow<'a, str>,
    }
}

mod urban {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r##"
        input = _{ ^"urban" ~ WHITE_SPACE+ ~ text ~ (WHITE_SPACE+ ~ pager)? }
        text = { (!(WHITE_SPACE+ ~ pager) ~ ANY)+ }
        pager = _{ "#" ~ length ~ ("+" ~ offset)? | "+" ~ offset }
        length = { ASCII_DIGIT+ }
        offset = { ASCII_DIGIT+ }
    "##]
    pub struct Urban;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Urban {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let offset = parameter
                .get(&Rule::offset)
                .map(|x| x.parse().unwrap())
                .unwrap_or(0);
            let length = parameter
                .get(&Rule::length)
                .map(|x| x.parse().unwrap())
                .unwrap_or(1);

            let text = reqwest::Client::new()
                .get("https://api.urbandictionary.com/v0/define")
                .query(&[("term", parameter.get(&Rule::text).unwrap())])
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            let items = serde_json::from_str::<Response>(&text)
                .context(format!("json error: {text}"))?
                .list
                .into_iter();

            let output = items.skip(offset).map(|item| {
                [
                    MessageText {
                        style: Some(vec![Style::Bold]),
                        text: format!("{}:", item.word).into(),
                        ..Default::default()
                    },
                    " ".into(),
                    item.definition.into(),
                ]
            });

            if length != 0 {
                context.send_itr(output.take(length)).await
            } else {
                context.send_itr(output).await
            }
        }
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Response<'a> {
        #[serde(borrow)]
        list: Vec<Item<'a>>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Item<'a> {
        defid: u64,
        thumbs_up: u64,
        thumbs_down: u64,
        // sometimes definition need to be owned
        #[serde(borrow)]
        author: Cow<'a, str>,
        current_vote: &'a str,
        // sometimes definition need to be owned
        #[serde(borrow)]
        definition: Cow<'a, str>,
        permalink: &'a str,
        word: &'a str,
        written_on: &'a str,
        // sometimes example need to be owned
        #[serde(borrow)]
        example: Cow<'a, str>,
        //#[serde(borrow)]
        //sound_urls: Vec<&'a str>,
    }
}

mod ipapi {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
        input = _{ ^"ip" ~ WHITE_SPACE+ ~ addr }
        addr = { (!WHITE_SPACE ~ ANY)+ }
    "#]
    pub struct Ipapi;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Ipapi {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let ip = parameter.get(&Rule::addr).unwrap();

            let text = reqwest::Client::new()
                .get(format!("http://ip-api.com/json/{ip}"))
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            if let Ok(response) = serde_json::from_str::<Response>(&text) {
                context
                    .send_fmt(format!(
                        "{} {} {} {} {} / {} {} {}",
                        response.country,
                        response.region_name,
                        response.city,
                        if response.lat.is_sign_negative() {
                            format!("{}°S", -response.lat)
                        } else {
                            format!("{}°N", response.lat)
                        },
                        if response.lon.is_sign_negative() {
                            format!("{}°W", -response.lon)
                        } else {
                            format!("{}°E", response.lon)
                        },
                        response.isp,
                        response.org,
                        response.r#as
                    ))
                    .await
            } else {
                let response = serde_json::from_str::<ResponseFail>(&text)
                    .context(format!("json error: {text}"))?;

                Err(Error::Message(response.message.into()))
            }
        }
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Response<'a> {
        status: &'a str,
        country: &'a str,
        #[serde(rename = "countryCode")]
        country_code: &'a str,
        region: &'a str,
        #[serde(rename = "regionName")]
        region_name: &'a str,
        city: &'a str,
        zip: &'a str,
        lat: f32,
        lon: f32,
        timezone: &'a str,
        isp: &'a str,
        org: &'a str,
        r#as: &'a str,
        query: &'a str,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct ResponseFail<'a> {
        status: &'a str,
        message: &'a str,
        query: &'a str,
    }
}

mod crates_io {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r##"
        input = _{ ^"crate" ~ WHITE_SPACE+ ~ text ~ (WHITE_SPACE+ ~ pager)? }
        text = { (!(WHITE_SPACE+ ~ pager) ~ ANY)+ }
        pager = _{ "#" ~ length ~ ("+" ~ offset)? | "+" ~ offset }
        length = { ASCII_DIGIT+ }
        offset = { ASCII_DIGIT+ }
    "##]
    pub struct CratesIo;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for CratesIo {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let offset = parameter
                .get(&Rule::offset)
                .map(|x| x.parse().unwrap())
                .unwrap_or(0);
            let length = parameter
                .get(&Rule::length)
                .map(|x| x.parse().unwrap())
                .unwrap_or(1);

            let text = reqwest::Client::builder()
                .user_agent("user/agent")
                .build()
                .context("client error")?
                .get("https://crates.io/api/v1/crates")
                .query(&[
                    ("page", "1"),
                    (
                        "per_page",
                        // NOTE 10 is the default value
                        &if length == 0 { 10 } else { length }.to_string(),
                    ),
                    ("q", parameter.get(&Rule::text).unwrap()),
                ])
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            let crates = serde_json::from_str::<Response>(&text)
                .context(format!("json error: {text}"))?
                .crates
                .into_iter();

            let output = crates.skip(offset).map(|item| {
                [
                    format!("{} [", item.name).into(),
                    MessageText::url(format!(" https://crates.io/crates/{} ", item.id).into()),
                    format!(
                        "] {} / {} recently / {}",
                        item.max_version, item.recent_downloads, item.description
                    )
                    .into(),
                ]
            });

            if length != 0 {
                context.send_itr(output.take(length)).await
            } else {
                context.send_itr(output).await
            }
        }
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Response<'a> {
        #[serde(borrow)]
        crates: Vec<Crate<'a>>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Crate<'a> {
        id: &'a str,
        name: &'a str,
        max_version: &'a str,
        #[serde(borrow)]
        description: Cow<'a, str>,
        downloads: u64,
        recent_downloads: u64,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }
}

mod movie {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r##"
        input = _{ ^"movie" ~ WHITE_SPACE+ ~ text ~ (WHITE_SPACE+ ~ pager)? }
        text = { (!(WHITE_SPACE+ ~ pager) ~ ANY)+ }
        pager = _{ "+" ~ offset }
        offset = { ASCII_DIGIT+ }
    "##]
    pub struct Movie;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Movie {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let offset = parameter
                .get(&Rule::offset)
                .map(|x| x.parse().unwrap())
                .unwrap_or(0);

            let text = reqwest::Client::new()
                .get("https://api.wmdb.tv/api/v1/movie/search")
                .query(&[("q", parameter.get(&Rule::text).unwrap())])
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            info!("{text}");

            let items = serde_json::from_str::<Vec<Item>>(&text)
                .context(format!("json error: {text}"))?
                .into_iter()
                .filter(|x| x.imdb_id.is_some());

            let item = items.skip(offset).next().ok_or(Error::NoOutput)?;

            context
                .send_fmt([
                    item.original_name.as_ref().into(),
                    " [".into(),
                    MessageText::url(
                        format!(" https://movie.douban.com/subject/{}/ ", item.douban_id).into(),
                    ),
                    format!("] {}", {
                        let mut buffer = Vec::new();

                        if item.data[0].name != item.original_name {
                            buffer.push(format!("aka {}", item.data[0].name));
                        }

                        if let Some(date) = item.date_released {
                            buffer.push(format!("{}", date));
                        }
                        buffer.push(format!("{}", item.data[0].genre.replace("/", " ")));
                        buffer.push(format!(
                            "{} {} {}%",
                            item.douban_rating,
                            item.imdb_rating.unwrap_or("0.0"),
                            item.rotten_rating.unwrap_or("0")
                        ));

                        buffer.join(" / ")
                    })
                    .into(),
                ])
                .await?;

            let mut data = MessageData::from_request_builder(
                reqwest::Client::new().get(item.data[0].poster.as_ref()),
                mime::IMAGE_JPEG,
            )
            .await?;
            data.text = Some(item.original_name.into());

            context.send_fmt(Message::Image(data)).await?;

            Ok(())
        }
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Item<'a> {
        #[serde(borrow)]
        data: Vec<Data<'a>>,
        #[serde(borrow)]
        #[serde(rename = "originalName")]
        original_name: Cow<'a, str>,
        #[serde(borrow)]
        #[serde(rename = "dateReleased")]
        date_released: Option<&'a str>,
        #[serde(rename = "doubanId")]
        douban_id: &'a str,
        #[serde(rename = "doubanRating")]
        douban_rating: &'a str,
        #[serde(default)]
        #[serde(rename = "imdbId")]
        #[serde(deserialize_with = "string_as_none")]
        imdb_id: Option<&'a str>,
        #[serde(default)]
        #[serde(rename = "imdbRating")]
        #[serde(deserialize_with = "string_as_none")]
        imdb_rating: Option<&'a str>,
        #[serde(default)]
        #[serde(rename = "rottenRating")]
        #[serde(deserialize_with = "string_as_none")]
        rotten_rating: Option<&'a str>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Data<'a> {
        #[serde(borrow)]
        name: Cow<'a, str>,
        #[serde(borrow)]
        genre: Cow<'a, str>,
        #[serde(borrow)]
        description: Cow<'a, str>,
        #[serde(borrow)]
        poster: Cow<'a, str>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    // see [](https://github.com/serde-rs/serde/issues/1425)
    fn string_as_none<'de, 'a, D>(de: D) -> Result<Option<&'a str>, D::Error>
    where
        D: serde::Deserializer<'de>,
        'de: 'a,
    {
        let tmp = Option::<&str>::deserialize(de)?;
        match tmp {
            None | Some("" | "null") => Ok(None),
            _ => Ok(tmp),
        }
    }
}

// google translate tk
// also used by baidu translate
mod google_translate {
    fn rl(mut num: i64, ops: &str) -> i64 {
        for slice in ops.chars().collect::<Vec<_>>().chunks(3) {
            if let &[op1, op2, op3] = slice {
                let n = if op3 >= 'a' {
                    op3 as u32 - 87
                } else {
                    op3.to_digit(10).unwrap()
                };
                let n = if op2 == '+' {
                    ((num as u64) >> n) as i64
                } else {
                    num << n
                };
                num = if op1 == '+' {
                    num + n & 4294967295
                } else {
                    num ^ n
                };
            }
        }

        num
    }

    pub fn tk(text: &str, n1: i64, n2: i64) -> String {
        let mut vec = Vec::new();

        let mut iter = text.chars().map(|x| x as u32).peekable();
        while let Some(mut a) = iter.next() {
            if 128 > a {
                vec.push(a);
            } else {
                if 2048 > a {
                    vec.push(a >> 6 | 192);
                } else {
                    if 55296 == (a & 64512)
                        && iter.peek().is_some()
                        && 56320 == (iter.peek().unwrap() & 64512)
                    {
                        let b = iter.next().unwrap();
                        a = 65536 + ((a & 1023) << 10) + (b & 1023);
                        vec.push(a >> 18 | 240);
                        vec.push(a >> 12 & 63 | 128);
                    } else {
                        vec.push(a >> 12 | 224);
                    }
                    vec.push(a >> 6 & 63 | 128);
                }
                vec.push(a & 63 | 128);
            }
        }

        let mut num = n1;
        for n in vec.into_iter() {
            num += n as i64;
            num = rl(num, "+-a^+6");
        }
        num = rl(num, "+-3^+b+-f");
        num ^= n2;
        if 0 > num {
            num = (num & 2147483647) + 2147483648;
        }
        num %= 1000000;

        format!("{num}.{}", num ^ n1)
    }
}

mod gtran {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r##"
        input = _{ ^"gtran" ~ (WHITE_SPACE+ ~ (source ~ ":" ~ target? | ":" ~ target))? ~ WHITE_SPACE+ ~ text }
        text = { ANY+ }
        source = { ASCII_ALPHA+ }
        target = { ASCII_ALPHA+ }
    "##]
    pub struct Gtran {
        n1: i64,
        n2: i64,
    }

    #[derive(Debug, Deserialize, Serialize)]
    pub struct GtranConfig {
        pub n1: i64,
        pub n2: i64,
    }

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    impl Gtran {
        pub fn new(config: &GtranConfig) -> Self {
            Self {
                n1: config.n1,
                n2: config.n2,
            }
        }
    }

    #[async_trait]
    impl Command for Gtran {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let text = *parameter.get(&Rule::text).unwrap();
            let source = parameter.get(&Rule::source);
            let target = parameter.get(&Rule::target);

            match target {
                Some(&"audio") => {
                    let source = *source
                        .ok_or(Error::Message("please specify the input language".into()))?;
                    let len = text.chars().count();

                    if len > 200 {
                        return Err(Error::Message("input is toooooooooo long".into()));
                    }

                    let mut data = MessageData::from_request_builder(
                        reqwest::Client::builder()
                            .user_agent(super::USER_AGENT)
                            .build()
                            .context("client error")?
                            .get("https://translate.google.com/translate_tts")
                            .query(&[
                                ("client", "webapp"),
                                ("idx", "0"),
                                ("total", "1"),
                                // parameters
                                ("ie", "UTF-8"),
                                ("tl", source),
                                ("q", text),
                                ("textlen", &format!("{}", len)),
                                ("ttsspeed", "1.0"),
                                ("tk", &google_translate::tk(text, self.n1, self.n2)),
                            ]),
                        "audio/mpeg".parse().unwrap(),
                    )
                    .await?;
                    data.text = Some(text.into());

                    context.send_fmt(Message::Audio(data, None)).await
                }
                _ => {
                    let text = reqwest::Client::builder()
                        .user_agent(super::USER_AGENT)
                        .build()
                        .context("client error")?
                        .get("https://translate.google.com/translate_a/single")
                        .query(&[
                            ("client", "webapp"),
                            ("dt", "at"),
                            ("dt", "bd"),
                            ("dt", "ex"),
                            ("dt", "gt"),
                            ("dt", "ld"),
                            ("dt", "md"),
                            ("dt", "qca"),
                            ("dt", "rm"),
                            ("dt", "rw"),
                            ("dt", "sos"),
                            ("dt", "ss"),
                            ("dt", "t"),
                            ("kc", "1"),
                            ("source", "bh"),
                            ("ssel", "0"),
                            ("tsel", "0"),
                            // parameters
                            ("ie", "UTF-8"),
                            ("oe", "UTF-8"),
                            ("sl", *source.unwrap_or(&"auto")),
                            (
                                "tl",
                                match target {
                                    Some(&"lang" | &"speak") => "en",
                                    Some(&"zhs" | &"zh") | None => "zh-CN",
                                    Some(&"zht") => "zh-TW",
                                    Some(target) => *target,
                                },
                            ),
                            ("hl", "en"),
                            ("q", text),
                            ("tk", &google_translate::tk(text, self.n1, self.n2)),
                        ])
                        .send()
                        .await
                        .context("send error")?
                        .text()
                        .await
                        .context("read error")?;
                    info!("{text:?}");

                    let response = serde_json::from_str::<Response>(&text)
                        .context(format!("json error: {text}"))?
                        .0;

                    match target {
                        Some(&"lang") => context.send_fmt(response[2].as_str().unwrap()).await,
                        Some(&"speak") => {
                            let text = response[0]
                                .as_array()
                                .unwrap()
                                .into_iter()
                                .filter_map(|ele| {
                                    ele.as_array()
                                        .and_then(|x| x.get(3))
                                        .and_then(|x| x.as_str())
                                })
                                .collect::<String>();

                            if text.is_empty() {
                                Err(Error::NoOutput)
                            } else {
                                context.send_fmt(text).await
                            }
                        }
                        _ => {
                            let text = response[0]
                                .as_array()
                                .unwrap()
                                .into_iter()
                                .filter_map(|ele| {
                                    ele.as_array()
                                        .and_then(|x| x.get(0))
                                        .and_then(|x| x.as_str())
                                })
                                .collect::<String>();

                            if text.is_empty() {
                                Err(Error::NoOutput)
                            } else {
                                context.send_fmt(text).await
                            }
                        }
                    }
                }
            }
        }
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Response(Vec<Value>);
}

// see [](https://fanyi.baidu.com/)
// see [](https://github.com/hungtcs/baidu-fanyi-api)
// see [](https://blog.csdn.net/fan13938409755/article/details/123764084)
mod btran {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r##"
        input = _{ ^"btran" ~ (WHITE_SPACE+ ~ (source ~ ":" ~ target? | ":" ~ target))? ~ WHITE_SPACE+ ~ text }
        text = { ANY+ }
        source = { ASCII_ALPHA+ }
        target = { ASCII_ALPHA+ }
    "##]
    pub struct Btran {
        token: String,
        n1: i64,
        n2: i64,
        headers: reqwest::header::HeaderMap,
    }

    #[derive(Debug, Deserialize, Serialize)]
    pub struct BtranConfig {
        pub baiduid: String,
        pub token: String,
        pub n1: i64,
        pub n2: i64,
    }

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    impl Btran {
        pub fn new(config: &BtranConfig) -> Self {
            use reqwest::header::*;

            let cookie = vec![
                ("APPGUIDE_10_0_2", "1"),
                ("FANYI_WORD_SWITCH", "1"),
                ("HISTORY_SWITCH", "1"),
                ("REALTIME_TRANS_SWITCH", "1"),
                ("SOUND_PREFER_SWITCH", "1"),
                ("SOUND_SPD_SWITCH", "1"),
                ("Hm_lpvt_64ecd82404c51e03dc91cb9e8c025574", "1657360388"),
                ("Hm_lvt_64ecd82404c51e03dc91cb9e8c025574", "1657306301"),
                ("BAIDUID", &config.baiduid),
                ("BAIDUID_BFESS", &config.baiduid),
            ]
            .into_iter()
            .map(|(k, v)| format!("{k}={v}"))
            .collect::<Vec<_>>()
            .join(";");

            Self {
                token: config.token.to_owned(),
                n1: config.n1,
                n2: config.n2,
                headers: [
                    (USER_AGENT, super::USER_AGENT.parse().unwrap()),
                    (COOKIE, cookie.parse().unwrap()),
                ]
                .into_iter()
                .collect(),
            }
        }

        // BAIDUID and BAIDUID_BFESS in cookie need to be obtained from browser, otherwise won't work somehow
        #[allow(dead_code)]
        async fn initialize(&self) -> Result<(String, i64, i64), Error> {
            let response = reqwest::Client::new()
                .get("https://fanyi.baidu.com/")
                .headers(self.headers.clone())
                .send()
                .await
                .context("send error")?;

            let cookies = response.cookies().collect::<Vec<_>>();
            info!("{cookies:?}");

            let html = response.text().await.context("read error")?;

            let regex = Regex::new(r"token: '(.*?)'(?s:.*)window.gtk = '(.*?)'").unwrap();

            let captures = regex
                .captures(&html)
                .ok_or(Error::Message("failed to initialize".into()))?;

            let token = captures.get(1).unwrap().as_str().to_owned();
            let gtk = captures.get(2).unwrap().as_str().to_owned();

            let mut split = gtk.split(".");
            let n1 = split.next().map(|x| x.parse().unwrap()).unwrap_or(0);
            let n2 = split.next().map(|x| x.parse().unwrap()).unwrap_or(0);

            Ok((token, n1, n2))
        }

        #[allow(dead_code)]
        async fn get_language(&self, text: &str) -> Result<String, Error> {
            let text = reqwest::Client::new()
                .post("https://fanyi.baidu.com/langdetect")
                .form(&[("query", text)])
                .headers(self.headers.clone())
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            let language = serde_json::from_str::<ResponseDetect>(&text)
                .context(format!("json error: {text}"))?
                .lan;

            Ok(language.to_owned())
        }

        fn sign(&self, text: &str) -> String {
            let len = text.chars().count();
            let text = if len > 30 {
                Cow::Owned(
                    text.char_indices()
                        .filter_map(|(i, c)| {
                            if i < 10 || (len / 2 - 5 <= i && i < len / 2 + 5) || len - 10 <= i {
                                Some(c)
                            } else {
                                None
                            }
                        })
                        .collect(),
                )
            } else {
                Cow::Borrowed(text)
            };

            google_translate::tk(&text, self.n1, self.n2)
        }
    }

    #[async_trait]
    impl Command for Btran {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let text = *parameter.get(&Rule::text).unwrap();
            let source = parameter.get(&Rule::source);
            let target = parameter.get(&Rule::target);

            match target {
                _ => {
                    let text = reqwest::Client::new()
                        .post("https://fanyi.baidu.com/v2transapi")
                        .form(&[
                            ("domain", "common"),
                            ("simple_means_flag", "3"),
                            ("transtype", "translang"),
                            ("from", *source.unwrap_or(&"auto")),
                            (
                                "to",
                                match target {
                                    Some(&"lang") => "en",
                                    Some(&"zhs" | &"zh") | None => "zh",
                                    Some(&"zht") => "cht",
                                    Some(&"wy") => "wyw",
                                    Some(&"ja") => "jp",
                                    Some(target) => *target,
                                },
                            ),
                            ("query", text),
                            ("sign", &self.sign(text)),
                            ("token", &self.token),
                        ])
                        .headers(self.headers.clone())
                        .send()
                        .await
                        .context("send error")?
                        .text()
                        .await
                        .context("read error")?;

                    if let Ok(response) = serde_json::from_str::<Response>(&text) {
                        info!("{response:?}");

                        let translation = response.trans_result;

                        match target {
                            Some(&"lang") => context.send_fmt(translation.from).await,
                            Some(&"speak") => Err(Error::NoOutput),
                            _ => {
                                let text = translation
                                    .data
                                    .into_iter()
                                    .map(|ele| ele.dst)
                                    .collect::<String>();

                                if text.is_empty() {
                                    Err(Error::NoOutput)
                                } else {
                                    context.send_fmt(text).await
                                }
                            }
                        }
                    } else {
                        let response = serde_json::from_str::<ResponseFail>(&text)
                            .context(format!("json error: {text}"))?;

                        Err(Error::Message(response.errmsg.into()))
                    }
                }
            }
        }
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Response<'a> {
        #[serde(borrow)]
        trans_result: Translation<'a>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Translation<'a> {
        #[serde(borrow)]
        data: Vec<TranslationData<'a>>,
        from: &'a str,
        to: &'a str,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct TranslationData<'a> {
        #[serde(borrow)]
        dst: Cow<'a, str>,
        #[serde(borrow)]
        src: Cow<'a, str>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct ResponseFail<'a> {
        error: u64,
        errno: u64,
        errmsg: Cow<'a, str>,
        query: Option<Cow<'a, str>>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct ResponseDetect<'a> {
        error: u64,
        msg: &'a str,
        lan: &'a str,
    }
}

mod speedrun {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r##"
        input = _{ ^"speedrun" ~ WHITE_SPACE+ ~ text ~ (WHITE_SPACE+ ~ pager)? }
        text = { (!(WHITE_SPACE+ ~ pager) ~ ANY)+ }
        pager = _{ "+" ~ offset }
        offset = { ASCII_DIGIT+ }
    "##]
    pub struct Speedrun;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Speedrun {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let offset = parameter
                .get(&Rule::offset)
                .map(|x| x.parse().unwrap())
                .unwrap_or(0);

            let text = reqwest::Client::new()
                .get("https://www.speedrun.com/ajax_search.php")
                .query(&[("term", parameter.get(&Rule::text).unwrap())])
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            let items = serde_json::from_str::<Vec<Item>>(&text)
                .context(format!("json error: {text}"))?
                .into_iter();

            let item = items.skip(offset).next().ok_or(Error::NoOutput)?;

            if item.category == "No results" {
                Err(Error::NoOutput)
            } else {
                context
                    .send_fmt([
                        item.label.as_ref().into(),
                        " [".into(),
                        MessageText::url(format!(" https://www.speedrun.com/{} ", item.url).into()),
                        format!("] {}", item.category).into(),
                    ])
                    .await
            }
        }
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Item<'a> {
        #[serde(borrow)]
        label: Cow<'a, str>,
        #[serde(borrow)]
        url: Cow<'a, str>,
        category: &'a str,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }
}

mod bangumi {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r##"
        input = _{ ^"bangumi" ~ WHITE_SPACE+ ~ text ~ (WHITE_SPACE+ ~ pager)? }
        text = { (!(WHITE_SPACE+ ~ pager) ~ ANY)+ }
        pager = _{ "+" ~ offset }
        offset = { ASCII_DIGIT+ }
    "##]
    pub struct Bangumi;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Bangumi {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let offset = parameter
                .get(&Rule::offset)
                .map(|x| x.parse().unwrap())
                .unwrap_or(0);

            let text = reqwest::Client::new()
                .get(format!(
                    "https://api.bgm.tv/search/subject/{}",
                    parameter.get(&Rule::text).unwrap()
                ))
                .query(&[("responseGroup", "large")])
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            let items = serde_json::from_str::<Response>(&text)
                .context(format!("json error: {text}"))?
                .list
                .into_iter();

            let item = items.skip(offset).next().ok_or(Error::NoOutput)?;

            context
                .send_fmt([
                    item.name.as_ref().into(),
                    " [".into(),
                    MessageText::url(format!(" https://bgm.tv/subject/{} ", item.id).into()),
                    format!("] {}", {
                        let mut buffer = Vec::new();

                        if !item.name_cn.is_empty() {
                            buffer.push(format!("aka {}", item.name_cn));
                        }

                        buffer.push(format!("{}", item.air_date));

                        if let Some(rating) = item.rating {
                            buffer.push(match item.rank {
                                Some(rank) => format!(
                                    "{:.1} @ {rank}{}",
                                    rating.score,
                                    match rank % 10 {
                                        1 if rank % 100 != 11 => "st",
                                        2 if rank % 100 != 12 => "nd",
                                        3 if rank % 100 != 13 => "rd",
                                        _ => "th",
                                    }
                                ),
                                None => format!("{:.1}", rating.score),
                            });
                        } else {
                            buffer.push(format!("0.0"));
                        }

                        buffer.join(" / ")
                    })
                    .into(),
                ])
                .await?;

            let mut data = MessageData::from_request_builder(
                reqwest::Client::new().get(item.images.large.as_ref()),
                mime::IMAGE_JPEG,
            )
            .await?;
            data.text = Some(item.name.into());

            context.send_fmt(Message::Image(data)).await?;

            Ok(())
        }
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Response<'a> {
        results: u64,
        #[serde(borrow)]
        list: Vec<Item<'a>>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Item<'a> {
        id: u64,
        r#type: u64,
        #[serde(borrow)]
        name: Cow<'a, str>,
        #[serde(borrow)]
        name_cn: Cow<'a, str>,
        #[serde(borrow)]
        summary: Cow<'a, str>,
        air_date: &'a str,
        air_weekday: u64,
        rank: Option<u64>,
        rating: Option<Rating>,
        #[serde(borrow)]
        images: Image<'a>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Rating {
        total: u64,
        score: f64,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Image<'a> {
        #[serde(borrow)]
        large: Cow<'a, str>,
        #[serde(borrow)]
        common: Cow<'a, str>,
        #[serde(borrow)]
        medium: Cow<'a, str>,
        #[serde(borrow)]
        small: Cow<'a, str>,
        #[serde(borrow)]
        grid: Cow<'a, str>,
    }
}

mod poke {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r##"
        input = _{ ^"poke" ~ (WHITE_SPACE+ ~ ("#" ~ id | name))? }
        id = { ASCII_DIGIT+ }
        name = { ASCII_ALPHA+ }
    "##]
    pub struct Poke;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Poke {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let id = parameter
                .get(&Rule::id)
                .map(|id| id.parse::<u64>().unwrap())
                .or_else(|| {
                    // fuzzy search
                    parameter.get(&Rule::name).and_then(|name| {
                        let matcher = skim::SkimMatcherV2::default();
                        let query = name.to_lowercase();

                        let mut vector = POKEMON
                            .iter()
                            .filter_map(|(index, value)| {
                                matcher
                                    .fuzzy_match(value, &query)
                                    .map(|score| (score, *index))
                            })
                            .collect::<Vec<_>>();

                        if vector.is_empty() {
                            None
                        } else {
                            vector.sort();
                            Some(vector[0].1)
                        }
                    })
                })
                // random id
                .unwrap_or(rand::thread_rng().gen_range(1..=POKEMON.len().try_into().unwrap()));

            //let text = reqwest::Client::new()
            //    .get(format!("https://pokeapi.co/api/v2/pokemon/{id}/"))
            //    .send()
            //    .await
            //    .context("send error")?
            //    .text()
            //    .await
            //    .context("read error")?;

            //let (tag, vec, url) = v2::parse(&text)?;

            let text = reqwest::Client::new()
                .post(format!("https://beta.pokeapi.co/graphql/v1beta/"))
                .json(&graphql_v1::Request::new(id))
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            let (tag, vec, url) = graphql_v1::parse(&text)?;

            context.send_fmt(vec).await?;

            if let Some(url) = url {
                let mut data = MessageData::from_request_builder(
                    reqwest::Client::new().get(url),
                    mime::IMAGE_PNG,
                )
                .await?;
                data.text = Some(tag.into());

                context.send_fmt(Message::Image(data)).await?;
            }

            Ok(())
        }
    }

    mod v2 {
        use super::*;

        #[allow(dead_code)]
        pub(super) fn parse(text: &str) -> Result<(&str, Vec<MessageText>, Option<&str>), Error> {
            let result = serde_json::from_str::<ResponsePokemon>(&text)
                .context(format!("json error: {text}"))?;

            let mut vec = vec![
                format!("#{} ", result.id).into(),
                MessageText {
                    style: Some(vec![Style::Bold]),
                    text: result.name.into(),
                    ..Default::default()
                },
            ];

            vec.extend([" / ".into()]);

            // types
            vec.extend({
                let mut text = result.types.iter().map(|x| MessageText {
                    color: (
                        Some(Color::Rgba(match x.r#type.name {
                            "normal" => 0xa8a878ff,
                            "fighting" => 0xc03028ff,
                            "flying" => 0xa890f0ff,
                            "poison" => 0xa040a0ff,
                            "ground" => 0xe0c068ff,
                            "rock" => 0xb8a038ff,
                            "bug" => 0xa8b820ff,
                            "ghost" => 0x705898ff,
                            "steel" => 0xb8b8d0ff,
                            "fire" => 0xf08030ff,
                            "water" => 0x6890f0ff,
                            "grass" => 0x78c850ff,
                            "electric" => 0xf8d030ff,
                            "psychic" => 0xf85888ff,
                            "ice" => 0x98d8d8ff,
                            "dragon" => 0x7038f8ff,
                            "dark" => 0x705848ff,
                            "fairy" => 0xee99acff,
                            _ => 0,
                        })),
                        None,
                    ),
                    text: x.r#type.name.into(),
                    ..Default::default()
                });
                //.intersperse_with(|| " ".into())

                let mut buffer = Vec::new();

                if let Some(x) = text.next() {
                    buffer.push(x);
                }

                for x in text {
                    buffer.push(" ".into());
                    buffer.push(x);
                }

                buffer
            });

            vec.extend([" / ".into()]);

            // stats
            vec.extend([
                MessageText {
                    color: (Some(Color::Rgba(0xff5959ff)), None),
                    text: result.stats[0].base_stat.to_string().into(),
                    ..Default::default()
                },
                "·".into(),
                MessageText {
                    color: (Some(Color::Rgba(0xf5ac78ff)), None),
                    text: result.stats[1].base_stat.to_string().into(),
                    ..Default::default()
                },
                "·".into(),
                MessageText {
                    color: (Some(Color::Rgba(0xfae078ff)), None),
                    text: result.stats[2].base_stat.to_string().into(),
                    ..Default::default()
                },
                "·".into(),
                MessageText {
                    color: (Some(Color::Rgba(0x9db7f5ff)), None),
                    text: result.stats[3].base_stat.to_string().into(),
                    ..Default::default()
                },
                "·".into(),
                MessageText {
                    color: (Some(Color::Rgba(0xa7db8dff)), None),
                    text: result.stats[4].base_stat.to_string().into(),
                    ..Default::default()
                },
                "·".into(),
                MessageText {
                    color: (Some(Color::Rgba(0xfa92b2ff)), None),
                    text: result.stats[5].base_stat.to_string().into(),
                    ..Default::default()
                },
            ]);

            vec.extend([" / ".into()]);

            // abilities
            vec.extend([result
                .abilities
                .iter()
                .map(|x| {
                    if x.is_hidden {
                        Cow::Owned(format!("({})", x.ability.name))
                    } else {
                        Cow::Borrowed(x.ability.name)
                    }
                })
                .collect::<Vec<_>>()
                .join(" ")
                .into()]);

            Ok((
                result.name,
                vec,
                result.sprites.other.official_artwork.front_default,
            ))
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        struct ResponsePokemon<'a> {
            id: u64,
            name: &'a str,
            //order: u64,
            //base_experience: Option<u64>,
            //height: u64,
            //weight: u64,
            //is_default: bool,
            #[serde(borrow)]
            abilities: Vec<PokemonAbility<'a>>,
            #[serde(borrow)]
            types: Vec<PokemonType<'a>>,
            #[serde(borrow)]
            sprites: PokemonSprites<'a>,
            #[serde(borrow)]
            stats: Vec<PokemonStat<'a>>,
            #[serde(borrow)]
            #[serde(flatten)]
            raw: HashMap<&'a str, Value>,
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        struct PokemonAbility<'a> {
            is_hidden: bool,
            slot: u64,
            #[serde(borrow)]
            ability: Link<'a>,
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        struct PokemonType<'a> {
            slot: u64,
            #[serde(borrow)]
            r#type: Link<'a>,
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        pub(super) struct PokemonSprites<'a> {
            #[serde(borrow)]
            front_default: Option<&'a str>,
            #[serde(borrow)]
            front_female: Option<&'a str>,
            #[serde(borrow)]
            front_shiny: Option<&'a str>,
            #[serde(borrow)]
            front_shiny_female: Option<&'a str>,
            #[serde(borrow)]
            back_default: Option<&'a str>,
            #[serde(borrow)]
            back_female: Option<&'a str>,
            #[serde(borrow)]
            back_shiny: Option<&'a str>,
            #[serde(borrow)]
            back_shiny_female: Option<&'a str>,
            #[serde(borrow)]
            pub other: PokemonSpritesOther<'a>,
            #[serde(borrow)]
            #[serde(flatten)]
            raw: HashMap<&'a str, Value>,
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        pub(super) struct PokemonSpritesOther<'a> {
            #[serde(borrow)]
            dream_world: PokemonSpritesDreamWorld<'a>,
            #[serde(borrow)]
            home: PokemonSpritesHome<'a>,
            #[serde(borrow)]
            #[serde(rename = "official-artwork")]
            pub official_artwork: PokemonSpritesOfficialArtwork<'a>,
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        pub(super) struct PokemonSpritesDreamWorld<'a> {
            #[serde(borrow)]
            front_default: Option<&'a str>,
            #[serde(borrow)]
            front_female: Option<&'a str>,
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        pub(super) struct PokemonSpritesHome<'a> {
            #[serde(borrow)]
            front_default: Option<&'a str>,
            #[serde(borrow)]
            front_female: Option<&'a str>,
            #[serde(borrow)]
            front_shiny: Option<&'a str>,
            #[serde(borrow)]
            front_shiny_female: Option<&'a str>,
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        pub(super) struct PokemonSpritesOfficialArtwork<'a> {
            #[serde(borrow)]
            pub front_default: Option<&'a str>,
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        struct PokemonStat<'a> {
            base_stat: u64,
            effort: u64,
            #[serde(borrow)]
            #[serde(flatten)]
            raw: HashMap<&'a str, Value>,
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        struct Link<'a> {
            name: &'a str,
            url: &'a str,
        }
    }

    mod graphql_v1 {
        use super::*;

        #[allow(dead_code)]
        pub(super) fn parse(
            text: &str,
        ) -> Result<(String, Vec<MessageText>, Option<String>), Error> {
            let result = serde_json::from_str::<Response>(&text)
                .context(format!("json error: {text}"))?
                .data
                .pokemon_v2_pokemon
                .into_iter()
                .next()
                .ok_or(Error::NoOutput)?;

            let tag = result
                .pokemon_v2_pokemonspecy
                .pokemon_v2_pokemonspeciesnames[3]
                .name;

            let mut vec = vec![
                format!("#{} ", result.id).into(),
                MessageText {
                    style: Some(vec![Style::Bold]),
                    text: tag.into(),
                    ..Default::default()
                },
                format!(" aka {}", result.name).into(),
            ];

            vec.extend([" / ".into()]);

            // types
            vec.extend({
                let mut text = result.pokemon_v2_pokemontypes.iter().map(|x| MessageText {
                    color: (
                        Some(Color::Rgba(match x.pokemon_v2_type.name {
                            "normal" => 0xa8a878ff,
                            "fighting" => 0xc03028ff,
                            "flying" => 0xa890f0ff,
                            "poison" => 0xa040a0ff,
                            "ground" => 0xe0c068ff,
                            "rock" => 0xb8a038ff,
                            "bug" => 0xa8b820ff,
                            "ghost" => 0x705898ff,
                            "steel" => 0xb8b8d0ff,
                            "fire" => 0xf08030ff,
                            "water" => 0x6890f0ff,
                            "grass" => 0x78c850ff,
                            "electric" => 0xf8d030ff,
                            "psychic" => 0xf85888ff,
                            "ice" => 0x98d8d8ff,
                            "dragon" => 0x7038f8ff,
                            "dark" => 0x705848ff,
                            "fairy" => 0xee99acff,
                            _ => 0,
                        })),
                        None,
                    ),
                    text: x.pokemon_v2_type.pokemon_v2_typenames[3].name.into(),
                    ..Default::default()
                });
                //.intersperse_with(|| " ".into())

                let mut buffer = Vec::new();

                if let Some(x) = text.next() {
                    buffer.push(x);
                }

                for x in text {
                    buffer.push(" ".into());
                    buffer.push(x);
                }

                buffer
            });

            vec.extend([" / ".into()]);

            // stats
            vec.extend([
                MessageText {
                    color: (Some(Color::Rgba(0xff5959ff)), None),
                    text: result.pokemon_v2_pokemonstats[0]
                        .base_stat
                        .to_string()
                        .into(),
                    ..Default::default()
                },
                "·".into(),
                MessageText {
                    color: (Some(Color::Rgba(0xf5ac78ff)), None),
                    text: result.pokemon_v2_pokemonstats[1]
                        .base_stat
                        .to_string()
                        .into(),
                    ..Default::default()
                },
                "·".into(),
                MessageText {
                    color: (Some(Color::Rgba(0xfae078ff)), None),
                    text: result.pokemon_v2_pokemonstats[2]
                        .base_stat
                        .to_string()
                        .into(),
                    ..Default::default()
                },
                "·".into(),
                MessageText {
                    color: (Some(Color::Rgba(0x9db7f5ff)), None),
                    text: result.pokemon_v2_pokemonstats[3]
                        .base_stat
                        .to_string()
                        .into(),
                    ..Default::default()
                },
                "·".into(),
                MessageText {
                    color: (Some(Color::Rgba(0xa7db8dff)), None),
                    text: result.pokemon_v2_pokemonstats[4]
                        .base_stat
                        .to_string()
                        .into(),
                    ..Default::default()
                },
                "·".into(),
                MessageText {
                    color: (Some(Color::Rgba(0xfa92b2ff)), None),
                    text: result.pokemon_v2_pokemonstats[5]
                        .base_stat
                        .to_string()
                        .into(),
                    ..Default::default()
                },
            ]);

            vec.extend([" / ".into()]);

            // abilities
            vec.extend([result
                .pokemon_v2_pokemonabilities
                .iter()
                .map(|x| {
                    let name = x.pokemon_v2_ability.pokemon_v2_abilitynames[3].name;

                    if x.is_hidden {
                        Cow::Owned(format!("({name})",))
                    } else {
                        Cow::Borrowed(name)
                    }
                })
                .collect::<Vec<_>>()
                .join(" ")
                .into()]);

            let url = serde_json::from_str::<super::v2::PokemonSprites>(
                &result.pokemon_v2_pokemonsprites[0].sprites,
            )
            .context(format!("json error: {text}"))?
            .other
            .official_artwork
            .front_default
            .map(|x| x.to_owned());

            Ok((tag.to_string(), vec, url))
        }

        #[allow(dead_code)]
        #[derive(Debug, Default, Serialize)]
        pub(super) struct Request<'a> {
            query: &'a str,
            variables: RequestVariables,
        }

        #[allow(dead_code)]
        #[derive(Debug, Default, Serialize)]
        struct RequestVariables {
            id: u64,
        }

        impl<'a> Request<'a> {
            pub(super) fn new(id: u64) -> Self {
                Self {
                    query: QUERY,
                    variables: RequestVariables { id },
                }
            }
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        struct Response<'a> {
            #[serde(borrow)]
            data: ResponseData<'a>,
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        struct ResponseData<'a> {
            #[serde(borrow)]
            pokemon_v2_pokemon: Vec<ResponsePokemon<'a>>,
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        struct ResponsePokemon<'a> {
            id: u64,
            name: &'a str,
            #[serde(borrow)]
            pokemon_v2_pokemonspecy: PokemonSpecy<'a>,
            #[serde(borrow)]
            pokemon_v2_pokemontypes: Vec<PokemonType<'a>>,
            pokemon_v2_pokemonstats: Vec<PokemonStat>,
            #[serde(borrow)]
            pokemon_v2_pokemonabilities: Vec<PokemonAbility<'a>>,
            #[serde(borrow)]
            pokemon_v2_pokemonsprites: Vec<PokemonSprite<'a>>,
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        struct PokemonSpecy<'a> {
            name: &'a str,
            #[serde(borrow)]
            pokemon_v2_pokemonspeciesnames: Vec<Name<'a>>,
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        struct PokemonType<'a> {
            #[serde(borrow)]
            pokemon_v2_type: Type<'a>,
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        struct PokemonAbility<'a> {
            is_hidden: bool,
            #[serde(borrow)]
            pokemon_v2_ability: Ability<'a>,
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        struct PokemonStat {
            base_stat: u64,
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        struct PokemonSprite<'a> {
            sprites: Cow<'a, str>,
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        struct Type<'a> {
            name: &'a str,
            #[serde(borrow)]
            pokemon_v2_typenames: Vec<Name<'a>>,
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        struct Ability<'a> {
            name: &'a str,
            #[serde(borrow)]
            pokemon_v2_abilitynames: Vec<Name<'a>>,
        }

        #[allow(dead_code)]
        #[derive(Debug, Deserialize)]
        struct Name<'a> {
            name: &'a str,
        }

        const QUERY: &str = r#"
query ($id: Int) {
    pokemon_v2_pokemon(where: {id: {_eq: $id}}) {
        id
        name
        pokemon_v2_pokemonspecy {
            name
            pokemon_v2_pokemonspeciesnames(where: {language_id: {_in: [1, 4, 11, 12]}}) {
                name
            }
        }
        pokemon_v2_pokemontypes {
            pokemon_v2_type {
                name
                pokemon_v2_typenames(where: {language_id: {_in: [1, 4, 11, 12]}}) {
                    name
                }
            }
        }
        pokemon_v2_pokemonstats {
            base_stat
        }
        pokemon_v2_pokemonabilities {
            pokemon_v2_ability {
                name
                pokemon_v2_abilitynames(where: {language_id: {_in: [1, 4, 11, 12]}}) {
                    name
                }
            }
            is_hidden
        }
        pokemon_v2_pokemonsprites {
            sprites
        }
    }
}
        "#;
    }

    const POKEMON: [(u64, &str); 905] = [
        (1, "bulbasaur"),
        (2, "ivysaur"),
        (3, "venusaur"),
        (4, "charmander"),
        (5, "charmeleon"),
        (6, "charizard"),
        (7, "squirtle"),
        (8, "wartortle"),
        (9, "blastoise"),
        (10, "caterpie"),
        (11, "metapod"),
        (12, "butterfree"),
        (13, "weedle"),
        (14, "kakuna"),
        (15, "beedrill"),
        (16, "pidgey"),
        (17, "pidgeotto"),
        (18, "pidgeot"),
        (19, "rattata"),
        (20, "raticate"),
        (21, "spearow"),
        (22, "fearow"),
        (23, "ekans"),
        (24, "arbok"),
        (25, "pikachu"),
        (26, "raichu"),
        (27, "sandshrew"),
        (28, "sandslash"),
        (29, "nidoran-f"),
        (30, "nidorina"),
        (31, "nidoqueen"),
        (32, "nidoran-m"),
        (33, "nidorino"),
        (34, "nidoking"),
        (35, "clefairy"),
        (36, "clefable"),
        (37, "vulpix"),
        (38, "ninetales"),
        (39, "jigglypuff"),
        (40, "wigglytuff"),
        (41, "zubat"),
        (42, "golbat"),
        (43, "oddish"),
        (44, "gloom"),
        (45, "vileplume"),
        (46, "paras"),
        (47, "parasect"),
        (48, "venonat"),
        (49, "venomoth"),
        (50, "diglett"),
        (51, "dugtrio"),
        (52, "meowth"),
        (53, "persian"),
        (54, "psyduck"),
        (55, "golduck"),
        (56, "mankey"),
        (57, "primeape"),
        (58, "growlithe"),
        (59, "arcanine"),
        (60, "poliwag"),
        (61, "poliwhirl"),
        (62, "poliwrath"),
        (63, "abra"),
        (64, "kadabra"),
        (65, "alakazam"),
        (66, "machop"),
        (67, "machoke"),
        (68, "machamp"),
        (69, "bellsprout"),
        (70, "weepinbell"),
        (71, "victreebel"),
        (72, "tentacool"),
        (73, "tentacruel"),
        (74, "geodude"),
        (75, "graveler"),
        (76, "golem"),
        (77, "ponyta"),
        (78, "rapidash"),
        (79, "slowpoke"),
        (80, "slowbro"),
        (81, "magnemite"),
        (82, "magneton"),
        (83, "farfetchd"),
        (84, "doduo"),
        (85, "dodrio"),
        (86, "seel"),
        (87, "dewgong"),
        (88, "grimer"),
        (89, "muk"),
        (90, "shellder"),
        (91, "cloyster"),
        (92, "gastly"),
        (93, "haunter"),
        (94, "gengar"),
        (95, "onix"),
        (96, "drowzee"),
        (97, "hypno"),
        (98, "krabby"),
        (99, "kingler"),
        (100, "voltorb"),
        (101, "electrode"),
        (102, "exeggcute"),
        (103, "exeggutor"),
        (104, "cubone"),
        (105, "marowak"),
        (106, "hitmonlee"),
        (107, "hitmonchan"),
        (108, "lickitung"),
        (109, "koffing"),
        (110, "weezing"),
        (111, "rhyhorn"),
        (112, "rhydon"),
        (113, "chansey"),
        (114, "tangela"),
        (115, "kangaskhan"),
        (116, "horsea"),
        (117, "seadra"),
        (118, "goldeen"),
        (119, "seaking"),
        (120, "staryu"),
        (121, "starmie"),
        (122, "mr-mime"),
        (123, "scyther"),
        (124, "jynx"),
        (125, "electabuzz"),
        (126, "magmar"),
        (127, "pinsir"),
        (128, "tauros"),
        (129, "magikarp"),
        (130, "gyarados"),
        (131, "lapras"),
        (132, "ditto"),
        (133, "eevee"),
        (134, "vaporeon"),
        (135, "jolteon"),
        (136, "flareon"),
        (137, "porygon"),
        (138, "omanyte"),
        (139, "omastar"),
        (140, "kabuto"),
        (141, "kabutops"),
        (142, "aerodactyl"),
        (143, "snorlax"),
        (144, "articuno"),
        (145, "zapdos"),
        (146, "moltres"),
        (147, "dratini"),
        (148, "dragonair"),
        (149, "dragonite"),
        (150, "mewtwo"),
        (151, "mew"),
        (152, "chikorita"),
        (153, "bayleef"),
        (154, "meganium"),
        (155, "cyndaquil"),
        (156, "quilava"),
        (157, "typhlosion"),
        (158, "totodile"),
        (159, "croconaw"),
        (160, "feraligatr"),
        (161, "sentret"),
        (162, "furret"),
        (163, "hoothoot"),
        (164, "noctowl"),
        (165, "ledyba"),
        (166, "ledian"),
        (167, "spinarak"),
        (168, "ariados"),
        (169, "crobat"),
        (170, "chinchou"),
        (171, "lanturn"),
        (172, "pichu"),
        (173, "cleffa"),
        (174, "igglybuff"),
        (175, "togepi"),
        (176, "togetic"),
        (177, "natu"),
        (178, "xatu"),
        (179, "mareep"),
        (180, "flaaffy"),
        (181, "ampharos"),
        (182, "bellossom"),
        (183, "marill"),
        (184, "azumarill"),
        (185, "sudowoodo"),
        (186, "politoed"),
        (187, "hoppip"),
        (188, "skiploom"),
        (189, "jumpluff"),
        (190, "aipom"),
        (191, "sunkern"),
        (192, "sunflora"),
        (193, "yanma"),
        (194, "wooper"),
        (195, "quagsire"),
        (196, "espeon"),
        (197, "umbreon"),
        (198, "murkrow"),
        (199, "slowking"),
        (200, "misdreavus"),
        (201, "unown"),
        (202, "wobbuffet"),
        (203, "girafarig"),
        (204, "pineco"),
        (205, "forretress"),
        (206, "dunsparce"),
        (207, "gligar"),
        (208, "steelix"),
        (209, "snubbull"),
        (210, "granbull"),
        (211, "qwilfish"),
        (212, "scizor"),
        (213, "shuckle"),
        (214, "heracross"),
        (215, "sneasel"),
        (216, "teddiursa"),
        (217, "ursaring"),
        (218, "slugma"),
        (219, "magcargo"),
        (220, "swinub"),
        (221, "piloswine"),
        (222, "corsola"),
        (223, "remoraid"),
        (224, "octillery"),
        (225, "delibird"),
        (226, "mantine"),
        (227, "skarmory"),
        (228, "houndour"),
        (229, "houndoom"),
        (230, "kingdra"),
        (231, "phanpy"),
        (232, "donphan"),
        (233, "porygon2"),
        (234, "stantler"),
        (235, "smeargle"),
        (236, "tyrogue"),
        (237, "hitmontop"),
        (238, "smoochum"),
        (239, "elekid"),
        (240, "magby"),
        (241, "miltank"),
        (242, "blissey"),
        (243, "raikou"),
        (244, "entei"),
        (245, "suicune"),
        (246, "larvitar"),
        (247, "pupitar"),
        (248, "tyranitar"),
        (249, "lugia"),
        (250, "ho-oh"),
        (251, "celebi"),
        (252, "treecko"),
        (253, "grovyle"),
        (254, "sceptile"),
        (255, "torchic"),
        (256, "combusken"),
        (257, "blaziken"),
        (258, "mudkip"),
        (259, "marshtomp"),
        (260, "swampert"),
        (261, "poochyena"),
        (262, "mightyena"),
        (263, "zigzagoon"),
        (264, "linoone"),
        (265, "wurmple"),
        (266, "silcoon"),
        (267, "beautifly"),
        (268, "cascoon"),
        (269, "dustox"),
        (270, "lotad"),
        (271, "lombre"),
        (272, "ludicolo"),
        (273, "seedot"),
        (274, "nuzleaf"),
        (275, "shiftry"),
        (276, "taillow"),
        (277, "swellow"),
        (278, "wingull"),
        (279, "pelipper"),
        (280, "ralts"),
        (281, "kirlia"),
        (282, "gardevoir"),
        (283, "surskit"),
        (284, "masquerain"),
        (285, "shroomish"),
        (286, "breloom"),
        (287, "slakoth"),
        (288, "vigoroth"),
        (289, "slaking"),
        (290, "nincada"),
        (291, "ninjask"),
        (292, "shedinja"),
        (293, "whismur"),
        (294, "loudred"),
        (295, "exploud"),
        (296, "makuhita"),
        (297, "hariyama"),
        (298, "azurill"),
        (299, "nosepass"),
        (300, "skitty"),
        (301, "delcatty"),
        (302, "sableye"),
        (303, "mawile"),
        (304, "aron"),
        (305, "lairon"),
        (306, "aggron"),
        (307, "meditite"),
        (308, "medicham"),
        (309, "electrike"),
        (310, "manectric"),
        (311, "plusle"),
        (312, "minun"),
        (313, "volbeat"),
        (314, "illumise"),
        (315, "roselia"),
        (316, "gulpin"),
        (317, "swalot"),
        (318, "carvanha"),
        (319, "sharpedo"),
        (320, "wailmer"),
        (321, "wailord"),
        (322, "numel"),
        (323, "camerupt"),
        (324, "torkoal"),
        (325, "spoink"),
        (326, "grumpig"),
        (327, "spinda"),
        (328, "trapinch"),
        (329, "vibrava"),
        (330, "flygon"),
        (331, "cacnea"),
        (332, "cacturne"),
        (333, "swablu"),
        (334, "altaria"),
        (335, "zangoose"),
        (336, "seviper"),
        (337, "lunatone"),
        (338, "solrock"),
        (339, "barboach"),
        (340, "whiscash"),
        (341, "corphish"),
        (342, "crawdaunt"),
        (343, "baltoy"),
        (344, "claydol"),
        (345, "lileep"),
        (346, "cradily"),
        (347, "anorith"),
        (348, "armaldo"),
        (349, "feebas"),
        (350, "milotic"),
        (351, "castform"),
        (352, "kecleon"),
        (353, "shuppet"),
        (354, "banette"),
        (355, "duskull"),
        (356, "dusclops"),
        (357, "tropius"),
        (358, "chimecho"),
        (359, "absol"),
        (360, "wynaut"),
        (361, "snorunt"),
        (362, "glalie"),
        (363, "spheal"),
        (364, "sealeo"),
        (365, "walrein"),
        (366, "clamperl"),
        (367, "huntail"),
        (368, "gorebyss"),
        (369, "relicanth"),
        (370, "luvdisc"),
        (371, "bagon"),
        (372, "shelgon"),
        (373, "salamence"),
        (374, "beldum"),
        (375, "metang"),
        (376, "metagross"),
        (377, "regirock"),
        (378, "regice"),
        (379, "registeel"),
        (380, "latias"),
        (381, "latios"),
        (382, "kyogre"),
        (383, "groudon"),
        (384, "rayquaza"),
        (385, "jirachi"),
        (386, "deoxys"),
        (387, "turtwig"),
        (388, "grotle"),
        (389, "torterra"),
        (390, "chimchar"),
        (391, "monferno"),
        (392, "infernape"),
        (393, "piplup"),
        (394, "prinplup"),
        (395, "empoleon"),
        (396, "starly"),
        (397, "staravia"),
        (398, "staraptor"),
        (399, "bidoof"),
        (400, "bibarel"),
        (401, "kricketot"),
        (402, "kricketune"),
        (403, "shinx"),
        (404, "luxio"),
        (405, "luxray"),
        (406, "budew"),
        (407, "roserade"),
        (408, "cranidos"),
        (409, "rampardos"),
        (410, "shieldon"),
        (411, "bastiodon"),
        (412, "burmy"),
        (413, "wormadam"),
        (414, "mothim"),
        (415, "combee"),
        (416, "vespiquen"),
        (417, "pachirisu"),
        (418, "buizel"),
        (419, "floatzel"),
        (420, "cherubi"),
        (421, "cherrim"),
        (422, "shellos"),
        (423, "gastrodon"),
        (424, "ambipom"),
        (425, "drifloon"),
        (426, "drifblim"),
        (427, "buneary"),
        (428, "lopunny"),
        (429, "mismagius"),
        (430, "honchkrow"),
        (431, "glameow"),
        (432, "purugly"),
        (433, "chingling"),
        (434, "stunky"),
        (435, "skuntank"),
        (436, "bronzor"),
        (437, "bronzong"),
        (438, "bonsly"),
        (439, "mime-jr"),
        (440, "happiny"),
        (441, "chatot"),
        (442, "spiritomb"),
        (443, "gible"),
        (444, "gabite"),
        (445, "garchomp"),
        (446, "munchlax"),
        (447, "riolu"),
        (448, "lucario"),
        (449, "hippopotas"),
        (450, "hippowdon"),
        (451, "skorupi"),
        (452, "drapion"),
        (453, "croagunk"),
        (454, "toxicroak"),
        (455, "carnivine"),
        (456, "finneon"),
        (457, "lumineon"),
        (458, "mantyke"),
        (459, "snover"),
        (460, "abomasnow"),
        (461, "weavile"),
        (462, "magnezone"),
        (463, "lickilicky"),
        (464, "rhyperior"),
        (465, "tangrowth"),
        (466, "electivire"),
        (467, "magmortar"),
        (468, "togekiss"),
        (469, "yanmega"),
        (470, "leafeon"),
        (471, "glaceon"),
        (472, "gliscor"),
        (473, "mamoswine"),
        (474, "porygon-z"),
        (475, "gallade"),
        (476, "probopass"),
        (477, "dusknoir"),
        (478, "froslass"),
        (479, "rotom"),
        (480, "uxie"),
        (481, "mesprit"),
        (482, "azelf"),
        (483, "dialga"),
        (484, "palkia"),
        (485, "heatran"),
        (486, "regigigas"),
        (487, "giratina"),
        (488, "cresselia"),
        (489, "phione"),
        (490, "manaphy"),
        (491, "darkrai"),
        (492, "shaymin"),
        (493, "arceus"),
        (494, "victini"),
        (495, "snivy"),
        (496, "servine"),
        (497, "serperior"),
        (498, "tepig"),
        (499, "pignite"),
        (500, "emboar"),
        (501, "oshawott"),
        (502, "dewott"),
        (503, "samurott"),
        (504, "patrat"),
        (505, "watchog"),
        (506, "lillipup"),
        (507, "herdier"),
        (508, "stoutland"),
        (509, "purrloin"),
        (510, "liepard"),
        (511, "pansage"),
        (512, "simisage"),
        (513, "pansear"),
        (514, "simisear"),
        (515, "panpour"),
        (516, "simipour"),
        (517, "munna"),
        (518, "musharna"),
        (519, "pidove"),
        (520, "tranquill"),
        (521, "unfezant"),
        (522, "blitzle"),
        (523, "zebstrika"),
        (524, "roggenrola"),
        (525, "boldore"),
        (526, "gigalith"),
        (527, "woobat"),
        (528, "swoobat"),
        (529, "drilbur"),
        (530, "excadrill"),
        (531, "audino"),
        (532, "timburr"),
        (533, "gurdurr"),
        (534, "conkeldurr"),
        (535, "tympole"),
        (536, "palpitoad"),
        (537, "seismitoad"),
        (538, "throh"),
        (539, "sawk"),
        (540, "sewaddle"),
        (541, "swadloon"),
        (542, "leavanny"),
        (543, "venipede"),
        (544, "whirlipede"),
        (545, "scolipede"),
        (546, "cottonee"),
        (547, "whimsicott"),
        (548, "petilil"),
        (549, "lilligant"),
        (550, "basculin"),
        (551, "sandile"),
        (552, "krokorok"),
        (553, "krookodile"),
        (554, "darumaka"),
        (555, "darmanitan"),
        (556, "maractus"),
        (557, "dwebble"),
        (558, "crustle"),
        (559, "scraggy"),
        (560, "scrafty"),
        (561, "sigilyph"),
        (562, "yamask"),
        (563, "cofagrigus"),
        (564, "tirtouga"),
        (565, "carracosta"),
        (566, "archen"),
        (567, "archeops"),
        (568, "trubbish"),
        (569, "garbodor"),
        (570, "zorua"),
        (571, "zoroark"),
        (572, "minccino"),
        (573, "cinccino"),
        (574, "gothita"),
        (575, "gothorita"),
        (576, "gothitelle"),
        (577, "solosis"),
        (578, "duosion"),
        (579, "reuniclus"),
        (580, "ducklett"),
        (581, "swanna"),
        (582, "vanillite"),
        (583, "vanillish"),
        (584, "vanilluxe"),
        (585, "deerling"),
        (586, "sawsbuck"),
        (587, "emolga"),
        (588, "karrablast"),
        (589, "escavalier"),
        (590, "foongus"),
        (591, "amoonguss"),
        (592, "frillish"),
        (593, "jellicent"),
        (594, "alomomola"),
        (595, "joltik"),
        (596, "galvantula"),
        (597, "ferroseed"),
        (598, "ferrothorn"),
        (599, "klink"),
        (600, "klang"),
        (601, "klinklang"),
        (602, "tynamo"),
        (603, "eelektrik"),
        (604, "eelektross"),
        (605, "elgyem"),
        (606, "beheeyem"),
        (607, "litwick"),
        (608, "lampent"),
        (609, "chandelure"),
        (610, "axew"),
        (611, "fraxure"),
        (612, "haxorus"),
        (613, "cubchoo"),
        (614, "beartic"),
        (615, "cryogonal"),
        (616, "shelmet"),
        (617, "accelgor"),
        (618, "stunfisk"),
        (619, "mienfoo"),
        (620, "mienshao"),
        (621, "druddigon"),
        (622, "golett"),
        (623, "golurk"),
        (624, "pawniard"),
        (625, "bisharp"),
        (626, "bouffalant"),
        (627, "rufflet"),
        (628, "braviary"),
        (629, "vullaby"),
        (630, "mandibuzz"),
        (631, "heatmor"),
        (632, "durant"),
        (633, "deino"),
        (634, "zweilous"),
        (635, "hydreigon"),
        (636, "larvesta"),
        (637, "volcarona"),
        (638, "cobalion"),
        (639, "terrakion"),
        (640, "virizion"),
        (641, "tornadus"),
        (642, "thundurus"),
        (643, "reshiram"),
        (644, "zekrom"),
        (645, "landorus"),
        (646, "kyurem"),
        (647, "keldeo"),
        (648, "meloetta"),
        (649, "genesect"),
        (650, "chespin"),
        (651, "quilladin"),
        (652, "chesnaught"),
        (653, "fennekin"),
        (654, "braixen"),
        (655, "delphox"),
        (656, "froakie"),
        (657, "frogadier"),
        (658, "greninja"),
        (659, "bunnelby"),
        (660, "diggersby"),
        (661, "fletchling"),
        (662, "fletchinder"),
        (663, "talonflame"),
        (664, "scatterbug"),
        (665, "spewpa"),
        (666, "vivillon"),
        (667, "litleo"),
        (668, "pyroar"),
        (669, "flabebe"),
        (670, "floette"),
        (671, "florges"),
        (672, "skiddo"),
        (673, "gogoat"),
        (674, "pancham"),
        (675, "pangoro"),
        (676, "furfrou"),
        (677, "espurr"),
        (678, "meowstic"),
        (679, "honedge"),
        (680, "doublade"),
        (681, "aegislash"),
        (682, "spritzee"),
        (683, "aromatisse"),
        (684, "swirlix"),
        (685, "slurpuff"),
        (686, "inkay"),
        (687, "malamar"),
        (688, "binacle"),
        (689, "barbaracle"),
        (690, "skrelp"),
        (691, "dragalge"),
        (692, "clauncher"),
        (693, "clawitzer"),
        (694, "helioptile"),
        (695, "heliolisk"),
        (696, "tyrunt"),
        (697, "tyrantrum"),
        (698, "amaura"),
        (699, "aurorus"),
        (700, "sylveon"),
        (701, "hawlucha"),
        (702, "dedenne"),
        (703, "carbink"),
        (704, "goomy"),
        (705, "sliggoo"),
        (706, "goodra"),
        (707, "klefki"),
        (708, "phantump"),
        (709, "trevenant"),
        (710, "pumpkaboo"),
        (711, "gourgeist"),
        (712, "bergmite"),
        (713, "avalugg"),
        (714, "noibat"),
        (715, "noivern"),
        (716, "xerneas"),
        (717, "yveltal"),
        (718, "zygarde"),
        (719, "diancie"),
        (720, "hoopa"),
        (721, "volcanion"),
        (722, "rowlet"),
        (723, "dartrix"),
        (724, "decidueye"),
        (725, "litten"),
        (726, "torracat"),
        (727, "incineroar"),
        (728, "popplio"),
        (729, "brionne"),
        (730, "primarina"),
        (731, "pikipek"),
        (732, "trumbeak"),
        (733, "toucannon"),
        (734, "yungoos"),
        (735, "gumshoos"),
        (736, "grubbin"),
        (737, "charjabug"),
        (738, "vikavolt"),
        (739, "crabrawler"),
        (740, "crabominable"),
        (741, "oricorio"),
        (742, "cutiefly"),
        (743, "ribombee"),
        (744, "rockruff"),
        (745, "lycanroc"),
        (746, "wishiwashi"),
        (747, "mareanie"),
        (748, "toxapex"),
        (749, "mudbray"),
        (750, "mudsdale"),
        (751, "dewpider"),
        (752, "araquanid"),
        (753, "fomantis"),
        (754, "lurantis"),
        (755, "morelull"),
        (756, "shiinotic"),
        (757, "salandit"),
        (758, "salazzle"),
        (759, "stufful"),
        (760, "bewear"),
        (761, "bounsweet"),
        (762, "steenee"),
        (763, "tsareena"),
        (764, "comfey"),
        (765, "oranguru"),
        (766, "passimian"),
        (767, "wimpod"),
        (768, "golisopod"),
        (769, "sandygast"),
        (770, "palossand"),
        (771, "pyukumuku"),
        (772, "type-null"),
        (773, "silvally"),
        (774, "minior"),
        (775, "komala"),
        (776, "turtonator"),
        (777, "togedemaru"),
        (778, "mimikyu"),
        (779, "bruxish"),
        (780, "drampa"),
        (781, "dhelmise"),
        (782, "jangmo-o"),
        (783, "hakamo-o"),
        (784, "kommo-o"),
        (785, "tapu-koko"),
        (786, "tapu-lele"),
        (787, "tapu-bulu"),
        (788, "tapu-fini"),
        (789, "cosmog"),
        (790, "cosmoem"),
        (791, "solgaleo"),
        (792, "lunala"),
        (793, "nihilego"),
        (794, "buzzwole"),
        (795, "pheromosa"),
        (796, "xurkitree"),
        (797, "celesteela"),
        (798, "kartana"),
        (799, "guzzlord"),
        (800, "necrozma"),
        (801, "magearna"),
        (802, "marshadow"),
        (803, "poipole"),
        (804, "naganadel"),
        (805, "stakataka"),
        (806, "blacephalon"),
        (807, "zeraora"),
        (808, "meltan"),
        (809, "melmetal"),
        (810, "grookey"),
        (811, "thwackey"),
        (812, "rillaboom"),
        (813, "scorbunny"),
        (814, "raboot"),
        (815, "cinderace"),
        (816, "sobble"),
        (817, "drizzile"),
        (818, "inteleon"),
        (819, "skwovet"),
        (820, "greedent"),
        (821, "rookidee"),
        (822, "corvisquire"),
        (823, "corviknight"),
        (824, "blipbug"),
        (825, "dottler"),
        (826, "orbeetle"),
        (827, "nickit"),
        (828, "thievul"),
        (829, "gossifleur"),
        (830, "eldegoss"),
        (831, "wooloo"),
        (832, "dubwool"),
        (833, "chewtle"),
        (834, "drednaw"),
        (835, "yamper"),
        (836, "boltund"),
        (837, "rolycoly"),
        (838, "carkol"),
        (839, "coalossal"),
        (840, "applin"),
        (841, "flapple"),
        (842, "appletun"),
        (843, "silicobra"),
        (844, "sandaconda"),
        (845, "cramorant"),
        (846, "arrokuda"),
        (847, "barraskewda"),
        (848, "toxel"),
        (849, "toxtricity"),
        (850, "sizzlipede"),
        (851, "centiskorch"),
        (852, "clobbopus"),
        (853, "grapploct"),
        (854, "sinistea"),
        (855, "polteageist"),
        (856, "hatenna"),
        (857, "hattrem"),
        (858, "hatterene"),
        (859, "impidimp"),
        (860, "morgrem"),
        (861, "grimmsnarl"),
        (862, "obstagoon"),
        (863, "perrserker"),
        (864, "cursola"),
        (865, "sirfetchd"),
        (866, "mr-rime"),
        (867, "runerigus"),
        (868, "milcery"),
        (869, "alcremie"),
        (870, "falinks"),
        (871, "pincurchin"),
        (872, "snom"),
        (873, "frosmoth"),
        (874, "stonjourner"),
        (875, "eiscue"),
        (876, "indeedee"),
        (877, "morpeko"),
        (878, "cufant"),
        (879, "copperajah"),
        (880, "dracozolt"),
        (881, "arctozolt"),
        (882, "dracovish"),
        (883, "arctovish"),
        (884, "duraludon"),
        (885, "dreepy"),
        (886, "drakloak"),
        (887, "dragapult"),
        (888, "zacian"),
        (889, "zamazenta"),
        (890, "eternatus"),
        (891, "kubfu"),
        (892, "urshifu"),
        (893, "zarude"),
        (894, "regieleki"),
        (895, "regidrago"),
        (896, "glastrier"),
        (897, "spectrier"),
        (898, "calyrex"),
        (899, "wyrdeer"),
        (900, "kleavor"),
        (901, "ursaluna"),
        (902, "basculegion"),
        (903, "sneasler"),
        (904, "overqwil"),
        (905, "enamorus"),
    ];
}
