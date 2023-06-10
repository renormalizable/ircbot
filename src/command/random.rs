use anyhow::Context as _;
use async_trait::async_trait;
use pest_derive::Parser;
use rand::prelude::*;
use serde::Deserialize;
use serde_json::Value;
use std::borrow::Cow;
use std::collections::HashMap;

use super::*;

pub use leetcode::Leetcode;

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
                    .filter(|question| question.stat.frontend_question_id == question_id)
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
                    format!("#{} [", question.stat.frontend_question_id).into(),
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
        frontend_question_id: u64,
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
