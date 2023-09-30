use anyhow::Context as _;
use async_trait::async_trait;
use chrono::{DateTime, Utc};
use pest_derive::Parser;
use rand::prelude::*;
use serde::Deserialize;
use serde_json::Value;
use std::borrow::Cow;
use std::collections::HashMap;
use tracing::*;

use super::*;

pub use leetcode::Leetcode;
pub use roll::Roll;
pub use solar::Solar;

mod leetcode {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r##"
        input = _{ ^"leetcode" ~ (WHITE_SPACE+ ~ ("#" ~ id | difficulty))? }
        id = { ASCII_DIGIT+ }
        difficulty = { ^"easy" | ^"medium" | ^"hard" }
    "##]
    pub struct Leetcode;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Leetcode {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let text = reqwest::Client::new()
                .get("https://leetcode.com/api/problems/all/")
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            let questions = serde_json::from_str::<Response>(&text)
                .context(format!("json error: {text}"))?
                .stat_status_pairs
                .into_iter();

            let question = if let Some(id) = parameter.get(&Rule::id) {
                let question_id = id.parse::<u64>().unwrap();
                match questions
                    .filter(|question| question.stat.frontend_question_id == Some(question_id))
                    .next()
                {
                    Some(question) => question,
                    None => return Err(Error::Message("wrong id".into())),
                }
            } else if let Some(&difficulty) = parameter.get(&Rule::difficulty) {
                let level = match difficulty {
                    "easy" => 1,
                    "medium" => 2,
                    "hard" => 3,
                    _ => unreachable!(),
                };
                match questions
                    .filter(|question| question.difficulty.level == level)
                    .choose(&mut rand::thread_rng())
                {
                    Some(question) => question,
                    None => return Err(Error::Message("no question with this difficulty".into())),
                }
            } else {
                match questions.choose(&mut rand::thread_rng()) {
                    Some(question) => question,
                    None => return Err(Error::Message("no question".into())),
                }
            };

            context
                .send_fmt([
                    format!("#{} [", question.stat.frontend_question_id.unwrap_or(0)).into(),
                    MessageItem::url(
                        format!(
                            " https://leetcode.com/problems/{}/ ",
                            question.stat.question_title_slug,
                        )
                        .into(),
                    ),
                    format!(
                        "] {} / {} AC / {}%{}",
                        match question.difficulty.level {
                            1 => "easy",
                            2 => "medium",
                            3 => "hard",
                            _ => return Err(Error::Message("wrong difficulty".into())),
                        },
                        question.stat.total_acs,
                        (question.stat.total_acs as f64 * 100.
                            / question.stat.total_submitted as f64)
                            .round(),
                        if question.paid_only { " / $$$" } else { "" },
                    )
                    .into(),
                ])
                .await
        }
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Response<'a> {
        #[serde(borrow)]
        stat_status_pairs: Vec<Question<'a>>,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Question<'a> {
        #[serde(borrow)]
        stat: QuestionStat<'a>,
        difficulty: QuestionDifficulty,
        paid_only: bool,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct QuestionStat<'a> {
        question_id: u64,
        frontend_question_id: Option<u64>,
        total_acs: u64,
        total_submitted: u64,
        // sometimes question__title needs to be owned
        #[serde(borrow)]
        #[serde(rename = "question__title")]
        question_title: Cow<'a, str>,
        #[serde(rename = "question__title_slug")]
        question_title_slug: &'a str,
        #[serde(borrow)]
        #[serde(flatten)]
        raw: HashMap<&'a str, Value>,
    }

    #[derive(Debug, Deserialize)]
    struct QuestionDifficulty {
        level: u64,
    }
}

mod solar {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r##"
        input = _{ ^"solar" }
    "##]
    pub struct Solar;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Solar {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            _parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let text = reqwest::Client::new()
                .get("https://www.hamqsl.com/solarxml.php")
                .send()
                .await
                .context("send error")?
                .text()
                .await
                .context("read error")?;

            let data = quick_xml::de::from_str::<Response>(&text)
                .context(format!("json error: {text}"))?
                .solar_data;

            let band = data
                .calculated_conditions
                .band
                .into_iter()
                .map(
                    |Band {
                         name,
                         time,
                         condition,
                     }| ((name, time), condition),
                )
                .collect::<HashMap<_, _>>();

            let mut vec = Vec::new();

            vec.extend([
                format!(
                    "{} / {} min ago",
                    data.updated,
                    (Utc::now() - data.updated).num_minutes()
                )
                .into(),
                " / SFI ".into(),
                format!("{}", data.solar_flux).into(),
                " / SN ".into(),
                format!("{}", data.sun_spots).into(),
                " / A ".into(),
                format!("{}", data.a_index).into(),
                " / K ".into(),
                format!("{}", data.k_index).into(),
                " /".into(),
            ]);

            for name in ["80m-40m", "30m-20m", "17m-15m", "12m-10m"] {
                vec.extend([
                    " [ ".into(),
                    name.into(),
                    " ".into(),
                    band.get(&(name, Time::Day)).ok_or(Error::NoOutput)?.into(),
                    " ".into(),
                    band.get(&(name, Time::Night))
                        .ok_or(Error::NoOutput)?
                        .into(),
                    " ]".into(),
                ]);
            }

            context.send_fmt(vec).await
        }
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Response<'a> {
        #[serde(borrow)]
        #[serde(rename = "solardata")]
        solar_data: SolarData<'a>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct SolarData<'a> {
        source: &'a str,
        #[serde(deserialize_with = "date")]
        updated: DateTime<Utc>,
        #[serde(rename = "solarflux")]
        solar_flux: u64,
        #[serde(rename = "aindex")]
        a_index: u64,
        #[serde(rename = "kindex")]
        k_index: u64,
        #[serde(rename = "kindexnt")]
        k_index_nt: &'a str,
        #[serde(rename = "xray")]
        x_ray: &'a str,
        #[serde(rename = "sunspots")]
        sun_spots: u64,
        #[serde(rename = "heliumline")]
        helium_line: f64,
        #[serde(rename = "protonflux")]
        proton_flux: u64,
        // NOTE there is a typo
        #[serde(rename = "electonflux")]
        electron_flux: u64,
        aurora: u64,
        normalization: f64,
        #[serde(rename = "latdegree")]
        lat_degree: f64,
        #[serde(rename = "solarwind")]
        solar_wind: f64,
        #[serde(rename = "magneticfield")]
        magnetic_field: f64,
        #[serde(borrow)]
        #[serde(rename = "calculatedconditions")]
        calculated_conditions: Conditions<'a>,
        #[serde(borrow)]
        #[serde(rename = "calculatedvhfconditions")]
        calculated_vhf_confitions: VhfConditions<'a>,
        #[serde(rename = "geomagfield")]
        geomag_field: &'a str,
        #[serde(rename = "signalnoise")]
        signal_noise: &'a str,
        fof2: f64,
        #[serde(rename = "muffactor")]
        muf_factor: f64,
        muf: f64,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Conditions<'a> {
        #[serde(borrow)]
        band: Vec<Band<'a>>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Band<'a> {
        #[serde(rename = "@name")]
        name: &'a str,
        #[serde(rename = "@time")]
        time: Time,
        #[serde(rename = "$text")]
        condition: Condition,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize, Eq, Hash, PartialEq)]
    enum Time {
        #[serde(rename = "day")]
        Day,
        #[serde(rename = "night")]
        Night,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    enum Condition {
        Good,
        Fair,
        Poor,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct VhfConditions<'a> {
        #[serde(borrow)]
        phenomenon: Vec<Phenomenon<'a>>,
    }

    #[allow(dead_code)]
    #[derive(Debug, Deserialize)]
    struct Phenomenon<'a> {
        #[serde(rename = "@name")]
        name: &'a str,
        #[serde(rename = "@location")]
        location: &'a str,
        #[serde(rename = "$text")]
        condition: &'a str,
    }

    fn date<'de, D>(de: D) -> Result<DateTime<Utc>, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        let tmp = <&str>::deserialize(de)?;
        DateTime::parse_from_str(tmp, "%d %h %Y %H%M %Z")
            .map(|x| x.with_timezone(&Utc))
            .map_err(serde::de::Error::custom)
    }

    impl<'a> From<&Condition> for MessageItem<'a> {
        fn from(condition: &Condition) -> Self {
            Self {
                color: match condition {
                    Condition::Good => (Some(Color::Lime), None),
                    Condition::Fair => (Some(Color::Orange), None),
                    Condition::Poor => (Some(Color::Red), None),
                },
                text: Cow::Owned(format!("{:?}", condition)),
                ..Default::default()
            }
        }
    }
}

mod roll {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r##"
        input = _{ ^"roll" ~ WHITE_SPACE+ ~ expr ~ (WHITE_SPACE* ~ cmp ~ WHITE_SPACE* ~ val)? }
        expr = { (!(WHITE_SPACE* ~ cmp) ~ ANY)+ }
        cmp = { "==" | "!=" | ">" | "<" | ">=" | "<=" }
        val = { "-"? ~ ASCII_DIGIT+ }
    "##]
    pub struct Roll;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Roll {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let value = {
                let expression = expr::Expr::new(parameter.get(&Rule::expr).unwrap())?;

                info!("expression: {expression:?}");

                expression.evaluate()
            };

            let mut vec = vec![value.to_string().into()];

            if let Some(cmp) = parameter.get(&Rule::cmp) {
                let target = parameter.get(&Rule::val).unwrap().parse().unwrap();

                let test = match *cmp {
                    "==" => value == target,
                    "!=" => value != target,
                    ">" => value > target,
                    "<" => value < target,
                    ">=" => value >= target,
                    "<=" => value <= target,
                    _ => unreachable!(),
                };

                vec.extend([
                    " ".into(),
                    if test {
                        MessageItem {
                            color: (Some(Color::Lime), None),
                            text: "pass".into(),
                            ..Default::default()
                        }
                    } else {
                        MessageItem {
                            color: (Some(Color::Red), None),
                            text: "fail".into(),
                            ..Default::default()
                        }
                    },
                ]);
            };

            context.send_fmt(vec).await
        }
    }

    mod expr {
        use super::*;
        use pest::{
            iterators::Pairs,
            pratt_parser::{Assoc, Op, PrattParser},
            Parser,
        };
        use rand::distributions::Uniform;
        use std::rc::Rc;

        #[derive(Debug, Parser)]
        #[grammar_inline = r##"
            input = _{ SOI ~ WHITE_SPACE* ~ expr ~ WHITE_SPACE* ~ EOI }
            expr = { prefix? ~ WHITE_SPACE* ~ primary ~ (WHITE_SPACE* ~ infix ~ WHITE_SPACE* ~ prefix? ~ WHITE_SPACE* ~ primary)* }
            primary = _{ "(" ~ WHITE_SPACE* ~ expr ~ WHITE_SPACE* ~ ")" | dice | integer }
            prefix = _{ neg }
            infix = _{ add | sub | mul | div | rem }

            dice = { count ~ "d" ~ integer }
            count = { ASCII_DIGIT{0, 5} }
            integer = { ASCII_DIGIT+ }

            neg = { "-" }

            add = { "+" }
            sub = { "-" }
            mul = { "*" }
            div = { "/" }
            rem = { "%" }
        "##]
        pub enum Expr {
            Integer(i64),
            Dice(i64, i64),
            Neg(Rc<Expr>),
            Add(Rc<Expr>, Rc<Expr>),
            Sub(Rc<Expr>, Rc<Expr>),
            Mul(Rc<Expr>, Rc<Expr>),
            Div(Rc<Expr>, Rc<Expr>),
            Rem(Rc<Expr>, Rc<Expr>),
        }

        impl Expr {
            pub fn new(message: &str) -> Result<Self, Error> {
                let pratt = PrattParser::new()
                    .op(Op::infix(Rule::add, Assoc::Left) | Op::infix(Rule::sub, Assoc::Left))
                    .op(Op::infix(Rule::mul, Assoc::Left)
                        | Op::infix(Rule::div, Assoc::Left)
                        | Op::infix(Rule::rem, Assoc::Left))
                    .op(Op::prefix(Rule::neg));

                Self::parse(Rule::input, message)
                    .map(|mut rules| Self::descent(&pratt, rules.next().unwrap().into_inner()))
                    .map_err(|_| Error::Message("wrong expression".into()))
            }

            fn descent(pratt: &PrattParser<Rule>, pairs: Pairs<Rule>) -> Self {
                pratt
                    .map_primary(|primary| match primary.as_rule() {
                        Rule::expr => Self::descent(pratt, primary.into_inner()),
                        Rule::dice => {
                            let inner = primary.into_inner().collect::<Vec<_>>();

                            Self::Dice(
                                inner[0].as_str().parse().unwrap_or(1),
                                inner[1].as_str().parse().unwrap(),
                            )
                        }
                        Rule::integer => Self::Integer(primary.as_str().parse().unwrap()),
                        _ => unreachable!(),
                    })
                    .map_prefix(|prefix, rhs| match prefix.as_rule() {
                        Rule::neg => Self::Neg(rhs.into()),
                        _ => unreachable!(),
                    })
                    .map_infix(|lhs, infix, rhs| match infix.as_rule() {
                        Rule::add => Self::Add(lhs.into(), rhs.into()),
                        Rule::sub => Self::Sub(lhs.into(), rhs.into()),
                        Rule::mul => Self::Mul(lhs.into(), rhs.into()),
                        Rule::div => Self::Div(lhs.into(), rhs.into()),
                        Rule::rem => Self::Rem(lhs.into(), rhs.into()),
                        _ => unreachable!(),
                    })
                    .parse(pairs)
            }

            pub fn evaluate(&self) -> i64 {
                Self::evaluator(&mut rand::thread_rng(), &self)
            }

            fn evaluator<R>(rng: &mut R, expr: &Self) -> i64
            where
                R: rand::Rng + ?Sized,
            {
                match expr {
                    Self::Integer(i) => *i,
                    Self::Dice(_, 0) => 0,
                    Self::Dice(i, j) => {
                        let dice = Uniform::new_inclusive(1, *j);

                        (0..*i).map(|_| dice.sample(rng)).sum()
                    }
                    Self::Neg(rhs) => -Self::evaluator(rng, rhs),
                    Self::Add(lhs, rhs) => Self::evaluator(rng, lhs) + Self::evaluator(rng, rhs),
                    Self::Sub(lhs, rhs) => Self::evaluator(rng, lhs) - Self::evaluator(rng, rhs),
                    Self::Mul(lhs, rhs) => Self::evaluator(rng, lhs) * Self::evaluator(rng, rhs),
                    Self::Div(lhs, rhs) => Self::evaluator(rng, lhs) / Self::evaluator(rng, rhs),
                    Self::Rem(lhs, rhs) => Self::evaluator(rng, lhs) % Self::evaluator(rng, rhs),
                }
            }
        }
    }
}
