use anyhow::Context as _;
use async_trait::async_trait;
use pest_derive::Parser;
//use regex::Regex;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{borrow::Cow, collections::HashMap, fmt, time::Duration};
use tracing::*;

use super::*;

pub use music::Music;
pub use music_163::Music163;
pub use music_qq::MusicQQ;

// see [](https://github.com/enzeberg/tonzhon-music)
mod music {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r##"
        input = _{ ^"music" ~ (":" ~ provider)? ~ WHITE_SPACE+ ~ text ~ (WHITE_SPACE+ ~ pager)? }
        provider = { (!WHITE_SPACE ~ ANY)+ }
        text = { (!(WHITE_SPACE+ ~ pager) ~ ANY)+ }
        pager = _{ "+" ~ offset }
        offset = { ASCII_DIGIT+ }
    "##]
    pub struct Music;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    impl Music {
        async fn get_song<'a, T>(provider: &str, id: &T) -> Result<MessageData<'a>, Error>
        where
            T: fmt::Display,
        {
            let text = reqwest::Client::builder()
                .user_agent(super::USER_AGENT)
                .build()
                .context("client error")?
                .get(format!(
                    "https://tonzhon.com/secondhand_api/song_source/{provider}/{id}"
                ))
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            let source = serde_json::from_str::<ResponseSong>(&text)
                .context(format!("json error: {text}"))?
                .data
                .song_source;

            MessageData::from_request_builder(
                reqwest::Client::builder()
                    .user_agent(super::USER_AGENT)
                    .build()
                    .context("client error")?
                    .get(source),
                "audio/mpeg".parse().unwrap(),
            )
            .await
        }
    }

    #[async_trait]
    impl Command for Music {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let offset = parameter
                .get(&Rule::offset)
                .map_or(0, |x| x.parse().unwrap());

            let provider = match parameter.get(&Rule::provider) {
                Some(&"qq") => "qq",
                Some(&"netease" | &"163") | None => "netease",
                Some(&"kuwo") => "kuwo",
                _ => return Err(Error::Message("unknown input".into())),
            };

            let text = reqwest::Client::builder()
                .user_agent(super::USER_AGENT)
                .build()
                .context("client error")?
                .get("https://tonzhon.com/secondhand_api/search")
                .query(&[
                    ("platform", provider),
                    ("keyword", parameter.get(&Rule::text).unwrap()),
                ])
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            let song = serde_json::from_str::<Response>(&text)
                .context(format!("json error: {text}"))?
                .data
                .songs
                .into_iter()
                .filter(|song| !song.requiring_payment.as_bool())
                .skip(offset)
                .next()
                .ok_or(Error::NoOutput)?;

            let data = Self::get_song(provider, &song.original_id).await?;

            context
                .send_fmt(Message::Audio(
                    data,
                    format!(
                        "{} / by {} / in {}",
                        song.name,
                        song.artists
                            .iter()
                            .map(|x| x.name.as_ref())
                            .collect::<Vec<_>>()
                            .join(" "),
                        song.album.name
                    )
                    .into(),
                    None,
                ))
                .await
        }
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Response<'a> {
        success: bool,
        #[serde(borrow)]
        data: Data<'a>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Data<'a> {
        total: u64,
        #[serde(borrow)]
        songs: Vec<Song<'a>>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Song<'a> {
        #[serde(borrow)]
        #[serde(rename = "originalId")]
        original_id: Id<'a>,
        #[serde(borrow)]
        name: Cow<'a, str>,
        #[serde(borrow)]
        artists: Vec<Artist<'a>>,
        #[serde(borrow)]
        album: Album<'a>,
        #[serde(rename = "requiringPayment")]
        requiring_payment: Bool,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Artist<'a> {
        #[serde(borrow)]
        id: Id<'a>,
        #[serde(borrow)]
        name: Cow<'a, str>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Album<'a> {
        #[serde(borrow)]
        id: Id<'a>,
        #[serde(borrow)]
        name: Cow<'a, str>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct ResponseSong<'a> {
        success: bool,
        #[serde(borrow)]
        data: SongSource<'a>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct SongSource<'a> {
        #[serde(rename = "songSource")]
        song_source: &'a str,
    }

    #[derive(Debug, Deserialize)]
    #[serde(untagged)]
    enum Bool {
        Bool(bool),
        Integer(u64),
    }

    impl Bool {
        fn as_bool(&self) -> bool {
            match self {
                Self::Bool(false) | Self::Integer(0) => false,
                _ => true,
            }
        }
    }

    #[derive(Debug, Deserialize)]
    #[serde(untagged)]
    enum Id<'a> {
        String(&'a str),
        Integer(u64),
    }

    impl<'a> fmt::Display for Id<'a> {
        fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
            match self {
                Self::String(string) => write!(f, "{string}"),
                Self::Integer(integer) => write!(f, "{integer}"),
            }
        }
    }
}

// see [](https://github.com/feeluown/feeluown-netease/blob/master/fuo_netease/api.py)
mod music_163 {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r##"
        input = _{ ^"163" ~ WHITE_SPACE+ ~ text ~ (WHITE_SPACE+ ~ pager)? }
        text = { (!(WHITE_SPACE+ ~ pager) ~ ANY)+ }
        pager = _{ "+" ~ offset }
        offset = { ASCII_DIGIT+ }
    "##]
    pub struct Music163;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    impl Music163 {
        async fn weapi<T>(path: &str, data: &T) -> Result<String, Error>
        where
            T: Serialize + ?Sized,
        {
            let text = reqwest::Client::builder()
                .user_agent(super::USER_AGENT)
                .build()
                .context("client error")?
                .post(format!("https://music.163.com/weapi{path}"))
                .header("Referer", "https://music.163.com")
                .header("X-Real-IP", "118.88.88.88")
                .form(&encryption::encrypt(
                    &serde_json::to_string(data).context("json error")?,
                )?)
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            Ok(text)
        }

        async fn get_song<'a, T>(id: &T) -> Result<MessageData<'a>, Error>
        where
            T: fmt::Display,
        {
            let text = Self::weapi(
                //"/song/enhance/player/url",
                "/song/enhance/player/url/v1",
                &HashMap::from([
                    //("br", "128000"),
                    ("level", "standard"),
                    ("encodeType", "aac"),
                    ("ids", &format!("[{id}]")),
                ]),
            )
            .await?;

            let source = serde_json::from_str::<ResponseSong>(&text)
                .context(format!("json error: {text}"))?
                .data
                .into_iter()
                .next()
                .ok_or(Error::NoOutput)?;

            let mut data = MessageData::from_request_builder(
                reqwest::Client::builder()
                    .user_agent(super::USER_AGENT)
                    .build()
                    .context("client error")?
                    .get(source.url)
                    .header("Referer", "https://music.163.com")
                    .header("X-Real-IP", "118.88.88.88"),
                "audio/mp4".parse().unwrap(),
            )
            .await?;
            // NOTE the api reports wrong mime
            data.mime = infer::get(&data.data).map_or_else(
                || "audio/mp4".parse().unwrap(),
                |x| {
                    x.mime_type()
                        .replace("video", "audio")
                        .replace("m4a", "mp4")
                        .parse()
                        .unwrap()
                },
            );

            Ok(data)
        }
    }

    #[async_trait]
    impl Command for Music163 {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let offset = parameter
                .get(&Rule::offset)
                .map_or(0, |x| x.parse().unwrap());

            let text = Self::weapi(
                "/search/get",
                &HashMap::from([
                    ("limit", "30"),
                    ("offset", "0"),
                    ("total", "true"),
                    ("type", "1"),
                    ("s", parameter.get(&Rule::text).unwrap()),
                ]),
            )
            .await?;

            //info!("search: {:?}", serde_json::from_str::<Response>(&text));

            let song = serde_json::from_str::<Response>(&text)
                .context(format!("json error: {text}"))?
                .result
                .songs
                .into_iter()
                .filter(|song| song.fee == 0 || song.fee == 8)
                .skip(offset)
                .next()
                .ok_or(Error::NoOutput)?;

            let data = Self::get_song(&song.id).await?;

            context
                .send_fmt(Message::Audio(
                    data,
                    format!(
                        "{} / by {} / in {}",
                        song.name,
                        song.artists
                            .iter()
                            .map(|x| x.name.as_ref())
                            .collect::<Vec<_>>()
                            .join(" "),
                        song.album.name
                    )
                    // NOTE workaround file extension detection in matrix-rust-sdk
                    // see https://github.com/matrix-org/matrix-rust-sdk/blob/main/crates/matrix-sdk/src/media.rs
                    .replace(".", "")
                    .into(),
                    Some(Duration::from_millis(song.duration)),
                ))
                .await
        }
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Response<'a> {
        code: u64,
        #[serde(borrow)]
        result: ResultSong<'a>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct ResultSong<'a> {
        #[serde(borrow)]
        songs: Vec<Song<'a>>,
        #[serde(rename = "songCount")]
        song_count: u64,
        #[serde(rename = "hasMore")]
        has_more: bool,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Song<'a> {
        id: u64,
        #[serde(borrow)]
        name: Cow<'a, str>,
        #[serde(borrow)]
        artists: Vec<Artist<'a>>,
        #[serde(borrow)]
        album: Album<'a>,
        duration: u64,
        fee: u64,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Artist<'a> {
        id: u64,
        #[serde(borrow)]
        name: Cow<'a, str>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Album<'a> {
        id: u64,
        #[serde(borrow)]
        name: Cow<'a, str>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct ResponseSong<'a> {
        code: u64,
        #[serde(borrow)]
        data: Vec<SongSource<'a>>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct SongSource<'a> {
        url: &'a str,
        time: u64,
        size: u64,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    mod encryption {
        use super::*;
        use base64::Engine;

        const BASE64: base64::engine::GeneralPurpose = base64::engine::general_purpose::STANDARD;

        const IV: &'static [u8] = b"0102030405060708";
        const MODULUS: &'static [u8] = b"00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7";
        const NOUNCE: &'static [u8] = b"0CoJUm6Qyw8W8jud";
        const PUBKEY: &'static [u8] = b"010001";

        fn ran(len: usize) -> Vec<u8> {
            use rand::distributions::{Alphanumeric, DistString};

            Alphanumeric
                .sample_string(&mut rand::thread_rng(), len)
                .into_bytes()
        }

        fn aes(data: &[u8], key: &[u8]) -> String {
            use aes::cipher::{block_padding::Pkcs7, BlockEncryptMut, KeyIvInit};

            type Aes128CbcEnc = cbc::Encryptor<aes::Aes128Enc>;

            let encryptor = Aes128CbcEnc::new(key.into(), IV.into());

            BASE64.encode(encryptor.encrypt_padded_vec_mut::<Pkcs7>(data))
        }

        fn rsa(data: &[u8], pubkey: &[u8], modulus: &[u8]) -> String {
            use num_bigint_dig::BigUint;

            format!(
                "{:0256x}",
                BigUint::from_bytes_le(data).modpow(
                    &BigUint::parse_bytes(pubkey, 16).unwrap(),
                    &BigUint::parse_bytes(modulus, 16).unwrap(),
                )
            )
        }

        pub fn encrypt(data: &str) -> Result<HashMap<&str, String>, Error> {
            let key = ran(16);

            let par = aes(&aes(data.as_bytes(), NOUNCE).as_bytes(), &key);
            let key = rsa(&key, PUBKEY, MODULUS);

            Ok([("params", par), ("encSecKey", key)].into())
        }
    }
}

// see [](https://github.com/jsososo/QQMusicApi/issues/157#issuecomment-1193077789)
// see [](https://github.com/UnblockNeteaseMusic/server-rust)
// see [](https://api.bcrjl.com/apidetail/29.html)
// see [](https://api.qhsou.com/ipa/qqmusic.php)
mod music_qq {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r##"
        input = _{ ^"yqq" ~ WHITE_SPACE+ ~ text ~ (WHITE_SPACE+ ~ pager)? }
        text = { (!(WHITE_SPACE+ ~ pager) ~ ANY)+ }
        pager = _{ "+" ~ offset }
        offset = { ASCII_DIGIT+ }
    "##]
    pub struct MusicQQ;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    impl MusicQQ {
        async fn musicu<T>(data: &T) -> Result<String, Error>
        where
            T: Serialize + ?Sized,
        {
            let text = reqwest::Client::builder()
                .user_agent(super::USER_AGENT)
                .build()
                .context("client error")?
                .post(format!("https://u.y.qq.com/cgi-bin/musicu.fcg"))
                .header("Origin", "https://y.qq.com")
                .header("Referer", "https://y.qq.com")
                .json(data)
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            Ok(text)
        }

        async fn bcrjl<T>(id: &T) -> Result<String, Error>
        where
            T: Serialize + ?Sized,
        {
            let text = reqwest::Client::builder()
                .user_agent(super::USER_AGENT)
                .build()
                .context("client error")?
                .post(format!("https://api.bcrjl.com/api/qqmusic.php"))
                .query(&[("id", id)])
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            let url = serde_json::from_str::<ResponseBcrjl>(&text)
                .context(format!("json error: {text}"))?
                .purl;

            // change to a faster host
            //Ok(Regex::new(r"http.*?qq\.com")
            //    .unwrap()
            //    .replace(&url, "http://ws.stream.qqmusic.qq.com")
            //    .into())
            Ok(url.into())
        }

        async fn get_song<'a, T>(id: &T) -> Result<MessageData<'a>, Error>
        where
            T: fmt::Display,
        {
            let url = Self::bcrjl(&format!("{id}")).await?;

            let data = MessageData::from_request_builder(
                reqwest::Client::builder()
                    .user_agent(super::USER_AGENT)
                    .build()
                    .context("client error")?
                    .get(url)
                    .header("Origin", "https://y.qq.com")
                    .header("Referer", "https://y.qq.com"),
                "audio/mp4".parse().unwrap(),
            )
            .await?;

            if data.data.len() > 0 {
                Ok(data)
            } else {
                Err(Error::Message("rate limited?".into()))
            }
        }
    }

    #[async_trait]
    impl Command for MusicQQ {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let offset = parameter
                .get(&Rule::offset)
                .map_or(0, |x| x.parse().unwrap());

            let text = Self::musicu(&json!({
                "music.search.SearchCgiService": {
                    "method": "DoSearchForQQMusicDesktop",
                    "module": "music.search.SearchCgiService",
                    "param": {
                        "num_per_page": 40,
                        "page_num": 1,
                        "query": parameter.get(&Rule::text).unwrap(),
                        "search_type": 0,
                    },
                }
            }))
            .await?;

            //info!("search: {text}");
            //info!("search: {:?}", serde_json::from_str::<Response>(&text));

            let song = serde_json::from_str::<Response>(&text)
                .context(format!("json error: {text}"))?
                .result
                .data
                .body
                .song
                .list
                .into_iter()
                .filter(|song| song.file.b_30s == 0 && song.file.e_30s == 0)
                .skip(offset)
                .next()
                .ok_or(Error::NoOutput)?;

            //info!("song: {song:?}");

            let data = Self::get_song(&song.mid).await?;

            context
                .send_fmt(Message::Audio(
                    data,
                    format!(
                        "{} / by {} / in {}",
                        song.name,
                        song.singer
                            .iter()
                            .map(|x| x.name.as_ref())
                            .collect::<Vec<_>>()
                            .join(" "),
                        song.album.name
                    )
                    .into(),
                    Some(Duration::from_secs(song.interval)),
                ))
                .await
        }
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Response<'a> {
        code: u64,
        #[serde(borrow)]
        #[serde(rename = "music.search.SearchCgiService")]
        result: ResultSearch<'a>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct ResultSearch<'a> {
        code: u64,
        #[serde(borrow)]
        data: ResultData<'a>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct ResultData<'a> {
        #[serde(borrow)]
        body: ResultBody<'a>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct ResultBody<'a> {
        #[serde(borrow)]
        song: ResultSong<'a>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct ResultSong<'a> {
        #[serde(borrow)]
        list: Vec<Song<'a>>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Song<'a> {
        id: u64,
        mid: &'a str,
        #[serde(borrow)]
        name: Cow<'a, str>,
        #[serde(borrow)]
        singer: Vec<Singer<'a>>,
        #[serde(borrow)]
        album: Album<'a>,
        #[serde(borrow)]
        file: File<'a>,
        interval: u64,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Singer<'a> {
        id: u64,
        mid: &'a str,
        #[serde(borrow)]
        name: Cow<'a, str>,
        #[serde(borrow)]
        title: Cow<'a, str>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Album<'a> {
        id: u64,
        mid: &'a str,
        #[serde(borrow)]
        name: Cow<'a, str>,
        #[serde(borrow)]
        title: Cow<'a, str>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct File<'a> {
        b_30s: u64,
        e_30s: u64,
        try_begin: u64,
        try_end: u64,
        media_mid: &'a str,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct ResponseSong<'a> {
        code: u64,
        #[serde(borrow)]
        #[serde(rename = "req_0")]
        result: ResultSource<'a>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct ResultSource<'a> {
        code: u64,
        #[serde(borrow)]
        data: ResultSourceData<'a>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct ResultSourceData<'a> {
        #[serde(borrow)]
        midurlinfo: Vec<SongSource<'a>>,
        #[serde(borrow)]
        sip: Vec<Cow<'a, str>>,
        #[serde(rename = "testfile2g")]
        test_file_2g: Cow<'a, str>,
        #[serde(rename = "testfilewifi")]
        test_file_wifi: Cow<'a, str>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct SongSource<'a> {
        purl: Cow<'a, str>,
        //time: u64,
        //size: u64,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct ResponseBcrjl<'a> {
        code: &'a str,
        msg: &'a str,
        #[serde(borrow)]
        purl: Cow<'a, str>,
    }
}
