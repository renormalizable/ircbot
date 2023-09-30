use async_trait::async_trait;
use pest_derive::Parser;

use super::*;

pub use echo::Echo;
pub use lower::Lower;
pub use sleep::Sleep;
pub use upper::Upper;
pub use utc::Utc;

mod echo {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
        input = _{ ^"echo" ~ WHITE_SPACE ~ content }
        content = { ANY+ }
    "#]
    pub struct Echo;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Echo {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            context
                .send_direct(
                    context.target(),
                    (*parameter.get(&Rule::content).unwrap()).into(),
                )
                .await
        }
    }
}

mod lower {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
        input = _{ ^"lower" ~ WHITE_SPACE ~ content }
        content = { ANY+ }
    "#]
    pub struct Lower;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Lower {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            context
                .send_fmt(parameter.get(&Rule::content).unwrap().to_lowercase())
                .await
        }
    }
}

mod upper {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
        input = _{ ^"upper" ~ WHITE_SPACE ~ content }
        content = { ANY+ }
    "#]
    pub struct Upper;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Upper {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            context
                .send_fmt(parameter.get(&Rule::content).unwrap().to_uppercase())
                .await
        }
    }
}

mod utc {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
        input = _{ ^"utc" ~ (WHITE_SPACE+ ~ offset)? }
        offset = { ("+" | "-") ~ ASCII_DIGIT+ }
    "#]
    pub struct Utc;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Utc {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let offset = parameter
                .get(&Rule::offset)
                .map_or(0, |x| x.parse().unwrap());
            let timezone = chrono::FixedOffset::east_opt(offset * 3600)
                .ok_or(Error::Message("are you living on the Earth?".into()))?;

            context
                .send_fmt(chrono::Utc::now().with_timezone(&timezone).to_rfc3339())
                .await
        }
    }
}

mod sleep {
    use super::*;

    #[derive(Parser)]
    #[grammar_inline = r#"
        input = _{ ^"sleep" ~ WHITE_SPACE+ ~ duration }
        duration = { ASCII_DIGIT+ }
    "#]
    pub struct Sleep;

    impl Default for Rule {
        fn default() -> Self {
            Self::input
        }
    }

    #[async_trait]
    impl Command for Sleep {
        type Key = Rule;
        async fn execute(
            &self,
            context: &impl Context,
            parameter: Self::Parameter<'_>,
        ) -> Result<(), Error> {
            let duration = parameter.get(&Rule::duration).unwrap().parse().unwrap();

            tokio::time::sleep(tokio::time::Duration::from_secs(duration)).await;

            context.send_fmt("wake up").await
        }
    }
}
